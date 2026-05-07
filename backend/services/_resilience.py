"""
外部数据源调用的"容错性"工具
================================

业务背景：
    项目需要从 yfinance / akshare / baostock 拉取行情。这些三方接口
    经常出现：
        1. 短暂的网络抖动（TCP RST、连接超时、HTTP 5xx）
        2. 偶发的限流（429 / "too many requests"）
        3. 单次请求长时间无响应（卡死）

    如果不做防护，单点失败会拖垮整个数据更新批次，最严重时阻塞整个 FastAPI worker。

设计：
    1. ``with_retry``：装饰器，对易失败的外部函数加自动重试 + 超时上限
    2. ``ExternalAPIError``：统一对外抛出的异常类型，方便上层捕获
    3. 所有重试事件会写入 logger.warning，失败信息可追溯

使用：
    >>> from services._resilience import with_retry
    >>>
    >>> @with_retry(timeout=30, attempts=3)
    >>> def fetch_stock_data_yfinance(...):
    ...     return yf.download(...)

设计取舍：
    * 为什么不在每个 fetch 函数里 try/except？
        装饰器集中后，重试策略改一处生效，避免散落各处不一致
    * 为什么超时用 ``signal``/``threading``？
        yfinance/akshare 内部是同步 requests，无法 await
        用线程包裹再 ``Future.result(timeout=)`` 是兼容性最好的方案
"""
from __future__ import annotations

import functools
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Callable, Optional, Tuple, Type, TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    RetryError,
)

logger = logging.getLogger(__name__)

# 默认会触发重试的异常类型（网络相关 + 通用异常）
# 业务层抛出的异常（如 ValueError 表示数据格式错）不会重试
DEFAULT_RETRY_EXCEPTIONS: Tuple[Type[BaseException], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,  # socket.error 等
)


class ExternalAPIError(Exception):
    """统一的外部数据源调用失败异常"""

    def __init__(self, source: str, message: str, original: Optional[Exception] = None):
        self.source = source
        self.original = original
        super().__init__(f"[{source}] {message}")


T = TypeVar("T")


# 全局共享的执行器，避免每次调用都新建线程池
_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="data-fetch")


def _run_with_timeout(func: Callable[..., T], timeout: float, *args, **kwargs) -> T:
    """
    在线程中执行同步函数，最多等待 ``timeout`` 秒。
    超时后抛 TimeoutError；线程会被标记为 daemon，进程退出时不会阻塞。
    """
    future = _executor.submit(func, *args, **kwargs)
    try:
        return future.result(timeout=timeout)
    except FuturesTimeoutError as e:
        # 注意：这里只是放弃等待，底层线程仍在跑（Python 无法强制 kill 线程）
        # 但因为 ThreadPoolExecutor 会复用线程，单次超时不会泄漏资源
        raise TimeoutError(
            f"调用超时（{timeout}s），底层请求可能仍在后台执行"
        ) from e


def with_retry(
    *,
    timeout: float = 30.0,
    attempts: int = 3,
    min_wait: float = 2.0,
    max_wait: float = 10.0,
    exceptions: Tuple[Type[BaseException], ...] = DEFAULT_RETRY_EXCEPTIONS,
    source: str = "external",
):
    """
    给同步函数加"重试 + 超时"防护

    参数：
        timeout: 单次调用最长等待秒数
        attempts: 最大尝试次数（含首次），默认 3
        min_wait/max_wait: 指数退避的等待区间
        exceptions: 哪些异常会触发重试
        source: 日志中显示的数据源标签（yfinance / akshare 等）
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @retry(
            reraise=True,
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
        )
        def _attempt(*args, **kwargs) -> T:
            return _run_with_timeout(func, timeout, *args, **kwargs)

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return _attempt(*args, **kwargs)
            except RetryError as e:
                # tenacity 在 reraise=True 时不会用 RetryError 包，但保留兜底
                raise ExternalAPIError(source, str(e), original=e) from e
            except exceptions as e:
                # 重试 N 次仍然失败
                logger.error(
                    "[%s] 调用 %s 最终失败，已重试 %d 次：%s",
                    source,
                    func.__name__,
                    attempts,
                    e,
                )
                raise ExternalAPIError(
                    source,
                    f"{func.__name__} 重试 {attempts} 次后仍失败：{e}",
                    original=e,
                ) from e

        return wrapper

    return decorator


def safe_call(
    func: Callable[..., T],
    *args,
    default: Optional[T] = None,
    source: str = "external",
    **kwargs,
) -> Optional[T]:
    """
    "尽力而为"调用：失败时返回 ``default`` 而非抛异常。
    适合用在批量更新的循环里——单个资产失败不阻断整体。
    """
    try:
        return func(*args, **kwargs)
    except ExternalAPIError as e:
        logger.warning("[%s] 调用 %s 失败（已降级返回 default）：%s", source, func.__name__, e)
        return default
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "[%s] 调用 %s 出现未预期异常（已降级返回 default）：%s",
            source,
            func.__name__,
            e,
        )
        return default
