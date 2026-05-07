"""
定时任务调度器（APScheduler）
============================

业务背景：
    在 HuggingFace/Railway 等单进程部署场景下，行情数据更新依赖管理员手动点击
    "刷新"按钮——容易忘记，导致龙虎榜数据陈旧。本模块利用 APScheduler 在
    FastAPI 应用启动时挂载一个后台调度器，按 cron 自动跑批。

任务清单：
    1. 工作日 16:00（北京时间）触发 ``update_all_assets_data`` —— A 股收盘
       约 15:00，留 1 小时让交易所/数据源补完结算价
    2. 工作日 22:30（北京时间）补一次 —— 给美股、夜盘期货、晚补的指标兜底
    3. 周一至周日凌晨 03:00 健康自检 —— 确保 scheduler 自身没死

设计取舍：
    * 为何用 APScheduler 而非 Celery？
        Celery 需要单独的 broker（Redis/RabbitMQ），对个人项目过重。
        APScheduler 跟 FastAPI 同进程跑，零运维。
    * 为何 max_instances=1 且 coalesce=True？
        防止上一次 16:00 任务还没跑完，下一次 22:30 任务又抢库；
        coalesce 让错过的任务（比如服务重启错过 16:00）只补一次而非堆积多次。
    * 时区：北京时间 Asia/Shanghai
    * 启用控制：环境变量 ``SCHEDULER_ENABLED=true`` 才启动；
      本地开发默认关闭，避免 dev 环境频繁打 yfinance/akshare。
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# 全局单例（FastAPI lifespan 钩子中创建/销毁）
_scheduler: Optional[BackgroundScheduler] = None


def _scheduled_update_market_data() -> None:
    """
    定时拉取所有资产的最新行情。
    包了一层 try/except，防止单次失败把调度器搞挂。
    """
    # 延迟 import，避免循环依赖
    from database.config import SessionLocal
    from services.market_data import update_all_assets_data

    db = SessionLocal()
    try:
        logger.info("[scheduler] ========== 开始定时更新行情 ==========")
        result = update_all_assets_data(db, force=False)
        logger.info(
            "[scheduler] 定时更新完成：total=%s success=%s failed=%s",
            result.get("total"),
            result.get("success"),
            result.get("failed"),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("[scheduler] 定时更新发生未捕获异常: %s", e)
    finally:
        db.close()


def _scheduler_heartbeat() -> None:
    """凌晨健康自检，仅用于确认 scheduler 仍在运行。"""
    logger.info("[scheduler] heartbeat ok")


def init_scheduler() -> Optional[BackgroundScheduler]:
    """
    启动后台调度器。如果环境变量 ``SCHEDULER_ENABLED`` 不为 truthy，
    则跳过（默认本地开发不开）。
    """
    global _scheduler

    enabled = os.getenv("SCHEDULER_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
    if not enabled:
        logger.info("[scheduler] SCHEDULER_ENABLED 未启用，跳过定时任务初始化")
        return None

    if _scheduler is not None:
        logger.warning("[scheduler] 调度器已存在，跳过重复初始化")
        return _scheduler

    scheduler = BackgroundScheduler(
        timezone="Asia/Shanghai",
        job_defaults={
            "coalesce": True,         # 错过的任务合并为一次
            "max_instances": 1,       # 同一任务不并发
            "misfire_grace_time": 3600,  # 错过 1 小时内仍可补跑
        },
    )

    # 任务 1：工作日 16:00 主跑
    scheduler.add_job(
        _scheduled_update_market_data,
        trigger=CronTrigger(day_of_week="mon-fri", hour=16, minute=0),
        id="market_data_update_primary",
        name="行情数据每日主更新",
        replace_existing=True,
    )

    # 任务 2：工作日 22:30 兜底（美股、夜盘期货、补漏）
    scheduler.add_job(
        _scheduled_update_market_data,
        trigger=CronTrigger(day_of_week="mon-fri", hour=22, minute=30),
        id="market_data_update_secondary",
        name="行情数据夜间兜底更新",
        replace_existing=True,
    )

    # 任务 3：每天 03:00 健康自检
    scheduler.add_job(
        _scheduler_heartbeat,
        trigger=CronTrigger(hour=3, minute=0),
        id="scheduler_heartbeat",
        name="调度器心跳",
        replace_existing=True,
    )

    scheduler.start()
    _scheduler = scheduler

    jobs_info = ", ".join(f"{j.name} -> {j.trigger}" for j in scheduler.get_jobs())
    logger.info("[scheduler] 已启动，作业列表：%s", jobs_info)
    return scheduler


def shutdown_scheduler() -> None:
    """优雅关闭调度器（FastAPI shutdown 时调用）。"""
    global _scheduler
    if _scheduler is None:
        return
    try:
        _scheduler.shutdown(wait=False)
        logger.info("[scheduler] 已关闭")
    finally:
        _scheduler = None
