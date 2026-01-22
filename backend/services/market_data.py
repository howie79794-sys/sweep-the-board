"""市场数据服务
专门存放调用外部接口（如 yfinance）获取市场数据的逻辑
"""
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Dict, List
import json
import time
import random
import traceback
import re

from sqlalchemy.orm import Session
from database.models import Asset, MarketData
from config import BASELINE_DATE


def get_beijing_time() -> datetime:
    """
    获取当前北京时间 (CST, UTC+8)
    
    Returns:
        datetime: 当前北京时间的 datetime 对象
    """
    utc_now = datetime.now(timezone.utc)
    beijing_tz = timezone(timedelta(hours=8))
    beijing_time = utc_now.astimezone(beijing_tz)
    return beijing_time


def is_trading_hours() -> bool:
    """
    判断当前是否在A股交易时间内（北京时间 09:15 - 15:30）
    
    Returns:
        bool: True 表示在交易时间内，False 表示已收盘
    """
    beijing_time = get_beijing_time()
    current_time = beijing_time.time()
    
    # A股交易时间：09:15 - 15:30（包含集合竞价和收盘）
    market_open = datetime.strptime("09:15", "%H:%M").time()
    market_close = datetime.strptime("15:30", "%H:%M").time()
    
    return market_open <= current_time <= market_close


def is_trading_day(target_date: date) -> bool:
    """
    判断指定日期是否为交易日（北京时间）
    
    规则：
    1. 周末（周六、周日）不是交易日
    2. 法定节假日不是交易日（通过数据库历史数据判断，如果没有历史数据则默认是交易日）
    3. 工作日且非节假日 = 交易日
    
    Args:
        target_date: 目标日期
    
    Returns:
        bool: True 表示是交易日，False 表示非交易日
    """
    weekday = target_date.weekday()  # 0=Monday, 6=Sunday
    
    # 周末不是交易日
    if weekday >= 5:  # 5=Saturday, 6=Sunday
        return False
    
    # 工作日默认是交易日
    # 注：如需精确判断法定节假日，可使用 chinese_calendar 库
    # 当前实现：工作日默认是交易日
    return True


def should_skip_api_request(target_date: date, db: Optional[Session] = None, asset_id: Optional[int] = None) -> bool:
    """
    判断是否应该跳过 API 请求（日历过滤层）
    
    规则：
    - 非交易日不发起 API 请求，直接读库
    
    Args:
        target_date: 目标日期
        db: 数据库会话（可选）
        asset_id: 资产ID（可选）
    
    Returns:
        bool: True 表示应该跳过 API 请求，False 表示应该发起请求
    """
    # 非交易日跳过 API 请求
    if not is_trading_day(target_date):
        print(f"[市场数据] [日历过滤] 日期 {target_date} 是非交易日（周末），跳过 API 请求，直接读库")
        return True
    
    return False


def get_latest_trading_date(db: Session, asset_id: Optional[int] = None) -> date:
    """
    获取最新交易日（北京时间）
    
    逻辑：
    1. 获取当前北京时间
    2. 如果是周末（周六、周日），回溯到周五
    3. 如果是工作日，使用当前日期
    4. 如果提供了 asset_id，查询数据库中该资产的最新有数据日期作为参考
    
    Args:
        db: 数据库会话
        asset_id: 资产ID（可选），如果提供则查询该资产的最新数据日期
    
    Returns:
        date: 最新交易日的 date 对象
    """
    beijing_time = get_beijing_time()
    today = beijing_time.date()
    current_weekday = today.weekday()  # 0=Monday, 6=Sunday
    
    # 如果是周末，回溯到周五
    if current_weekday == 5:  # 周六
        latest_trading_date = today - timedelta(days=1)  # 周五
    elif current_weekday == 6:  # 周日
        latest_trading_date = today - timedelta(days=2)  # 周五
    else:
        latest_trading_date = today
    
    # 如果提供了 asset_id，查询数据库中该资产的最新有数据日期
    if asset_id:
        try:
            latest_data = db.query(MarketData).filter(
                MarketData.asset_id == asset_id
            ).order_by(MarketData.date.desc()).first()
            
            if latest_data and latest_data.date < latest_trading_date:
                # 如果数据库中的最新数据日期比计算出的交易日更早，使用数据库中的日期
                # 这可以处理节假日等情况
                pass  # 保持使用 latest_trading_date
            elif latest_data and latest_data.date > latest_trading_date:
                # 如果数据库中有未来的数据（不应该发生，但以防万一），使用数据库中的日期
                latest_trading_date = latest_data.date
        except Exception as e:
            print(f"[市场数据] 查询资产最新数据日期时发生异常: {type(e).__name__}: {str(e)}")
            # 继续使用计算出的日期
    
    return latest_trading_date

# 尝试导入 yfinance
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("[市场数据] 警告: yfinance 未安装")

# 尝试导入 akshare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("[市场数据] 警告: akshare 未安装")

# 尝试导入 baostock
try:
    import baostock as bs
    BAOSTOCK_AVAILABLE = True
except ImportError:
    BAOSTOCK_AVAILABLE = False
    print("[市场数据] 警告: baostock 未安装")


class YFinanceRateLimitError(RuntimeError):
    """yfinance 触发频率限制时抛出的异常。"""
    pass


def normalize_stock_code(code: str) -> str:
    """
    标准化股票代码格式
    支持多种输入格式：
    - SH601727 -> 601727
    - SZ300857 -> 300857
    - 601727.SH -> 601727
    - 300857.SZ -> 300857
    - 601727 -> 601727 (保持不变)
    """
    # 去掉市场后缀 (.SH, .SZ, .SS)
    code = code.replace(".SH", "").replace(".SZ", "").replace(".SS", "")
    # 去掉市场前缀 (SH, SZ)
    code = code.replace("SH", "").replace("SZ", "")
    return code


def convert_to_yfinance_symbol(code: str) -> str:
    """
    将A股代码转换为 yfinance 格式
    yfinance 使用 .SS (上海) 或 .SZ (深圳) 后缀
    
    规则：
    - 6开头 -> XXXXXX.SS (上海)
    - 0或3开头 -> XXXXXX.SZ (深圳)
    """
    clean_code = normalize_stock_code(code)
    
    if clean_code.startswith('6'):
        return f"{clean_code}.SS"  # 上海市场
    elif clean_code.startswith(('0', '3')):
        return f"{clean_code}.SZ"  # 深圳市场
    else:
        # 默认尝试上海市场
        print(f"[市场数据] 警告: 无法识别代码 {clean_code} 的市场，默认使用上海市场")
        return f"{clean_code}.SS"


def normalize_date_str(date_input) -> str:
    """
    将日期标准化为 YYYY-MM-DD 格式字符串
    
    Args:
        date_input: 日期输入，可以是 date 对象或字符串
    
    Returns:
        str: YYYY-MM-DD 格式的日期字符串
    
    Raises:
        ValueError: 如果无法解析日期格式
    """
    if isinstance(date_input, datetime):
        return date_input.date().strftime('%Y-%m-%d')
    if isinstance(date_input, date):
        return date_input.strftime('%Y-%m-%d')
    elif isinstance(date_input, str):
        cleaned = date_input.strip()
        try:
            for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y%m%d']:
                try:
                    date_obj = datetime.strptime(cleaned, fmt).date()
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            if re.fullmatch(r"\d{8}", cleaned):
                date_obj = datetime.strptime(cleaned, "%Y%m%d").date()
                return date_obj.strftime('%Y-%m-%d')
            date_obj = date.fromisoformat(cleaned.replace("/", "-"))
            return date_obj.strftime('%Y-%m-%d')
        except Exception as e:
            raise ValueError(f"无法解析日期格式: {date_input} (错误: {str(e)})")
    else:
        raise ValueError(f"不支持的日期类型: {type(date_input)}")


def format_date_for_baostock(date_input) -> str:
    """
    兼容旧调用：保持 YYYY-MM-DD 格式，避免错误转成 20260103
    """
    return normalize_date_str(date_input)


def is_a_share_code(code: str) -> bool:
    code_upper = code.upper().strip()
    return code_upper.startswith("SH.") or code_upper.startswith("SZ.")


def is_futures_main_code(code: str) -> bool:
    """
    判断是否为期货主力合约代码
    支持格式：
    - CF.IF0, CF.IC, CF.IM, CF.IH
    - IF0, IC, IM0, IH
    - IF=F, IC=F, IM=F, IH=F
    """
    code_upper = code.upper().strip()
    # 移除前缀标记
    code_clean = code_upper.replace("CF.", "").replace("=F", "")
    # 检查是否为股指期货代码
    return any(code_clean.startswith(prefix) for prefix in ["IF", "IC", "IM", "IH"])


def is_domestic_code(code: str) -> bool:
    return is_a_share_code(code) or is_futures_main_code(code)


def is_yfinance_rate_limit_error(error: Exception) -> bool:
    error_name = type(error).__name__
    error_msg = str(error).lower()
    return (
        "ratelimit" in error_msg
        or "too many requests" in error_msg
        or "429" in error_msg
        or "rate limit" in error_msg
        or "YFRateLimitError".lower() in error_name.lower()
    )


def fetch_financial_indicators_yfinance(ticker: yf.Ticker) -> Dict[str, float]:
    """
    从 yfinance ticker.info 获取财务指标
    
    Args:
        ticker: yfinance Ticker 对象
    
    Returns:
        dict: 包含财务指标的字典，如果获取失败则返回默认值
    """
    indicators = {
        "pe_ratio": 0.0,
        "pb_ratio": 0.0,
        "market_cap": 0.0,
        "eps_forecast": 0.0
    }
    
    if not YFINANCE_AVAILABLE:
        return indicators
    
    try:
        info = ticker.info
        
        # 获取 trailingPE (市盈率)
        if 'trailingPE' in info and info['trailingPE'] is not None:
            try:
                indicators["pe_ratio"] = float(info['trailingPE'])
            except (ValueError, TypeError):
                pass
        
        # 获取 priceToBook (市净率)
        if 'priceToBook' in info and info['priceToBook'] is not None:
            try:
                indicators["pb_ratio"] = float(info['priceToBook'])
            except (ValueError, TypeError):
                pass
        
        # 获取 marketCap (总市值)，转换为亿元
        # 检查多个可能的字段名
        market_cap_value = None
        
        # 优先尝试 marketCap
        if 'marketCap' in info and info['marketCap'] is not None:
            try:
                market_cap_value = float(info['marketCap'])
            except (ValueError, TypeError):
                pass
        
        # 如果上面没有获取到，尝试 market_cap (下划线格式)
        if market_cap_value is None and 'market_cap' in info and info['market_cap'] is not None:
            try:
                market_cap_value = float(info['market_cap'])
            except (ValueError, TypeError):
                pass
        
        # 如果获取到市值且大于0，转换为亿元
        if market_cap_value is not None and market_cap_value > 0:
            # 转换为亿元（除以 100,000,000）
            indicators["market_cap"] = market_cap_value / 100000000.0
            market_cap_str = f"{indicators['market_cap']:.2f}" if indicators['market_cap'] is not None else "N/A"
            print(f"[市场数据] [财务指标] 市值转换: 原始值={market_cap_value}, 转换后={market_cap_str}亿元")
        else:
            print(f"[市场数据] [财务指标] 警告: 市值获取失败或为0 (marketCap={info.get('marketCap')}, market_cap={info.get('market_cap')})")
        
        # 获取 EPS 预测 - 尝试多个可能的字段名
        eps_value = None
        
        # 优先尝试 earningsEstimateNextYear (未来一年 EPS 预测)
        if 'earningsEstimateNextYear' in info and info['earningsEstimateNextYear'] is not None:
            try:
                eps_value = float(info['earningsEstimateNextYear'])
            except (ValueError, TypeError):
                pass
        
        # 如果上面没有获取到，尝试 trailingEps (过去12个月 EPS)
        if eps_value is None and 'trailingEps' in info and info['trailingEps'] is not None:
            try:
                eps_value = float(info['trailingEps'])
            except (ValueError, TypeError):
                pass
        
        # 如果还是没有，尝试 forwardEps (预期 EPS)
        if eps_value is None and 'forwardEps' in info and info['forwardEps'] is not None:
            try:
                eps_value = float(info['forwardEps'])
            except (ValueError, TypeError):
                pass
        
        if eps_value is not None:
            indicators["eps_forecast"] = eps_value
        else:
            print(f"[市场数据] [财务指标] 警告: EPS获取失败，尝试的字段: earningsEstimateNextYear={info.get('earningsEstimateNextYear')}, trailingEps={info.get('trailingEps')}, forwardEps={info.get('forwardEps')}")
        
        # 打印获取结果（包括0值）
        pe_str = str(indicators['pe_ratio']) if indicators['pe_ratio'] is not None else "N/A"
        pb_str = str(indicators['pb_ratio']) if indicators['pb_ratio'] is not None else "N/A"
        market_cap_str = f"{indicators['market_cap']:.2f}" if indicators['market_cap'] is not None else "N/A"
        eps_str = str(indicators['eps_forecast']) if indicators['eps_forecast'] is not None else "N/A"
        print(f"[市场数据] [财务指标] 获取结果: PE={pe_str}, PB={pb_str}, 市值={market_cap_str}亿元, EPS预测={eps_str}")
        
    except Exception as e:
        print(f"[市场数据] [财务指标] 获取失败: {type(e).__name__}: {str(e)}")
        # 返回默认值，不中断流程
    
    return indicators


def fetch_realtime_price_yfinance(code: str) -> Optional[pd.DataFrame]:
    """
    使用 yfinance 获取盘中实时价格（仅在交易时间内使用）
    
    Args:
        code: 股票代码（支持多种格式）
    
    Returns:
        pd.DataFrame 或 None（失败时）
    """
    if not YFINANCE_AVAILABLE:
        return None
    
    try:
        print(f"[市场数据] [yfinance实时] 尝试获取实时价格: code={code}")
        
        # 转换为 yfinance 格式
        symbol = convert_to_yfinance_symbol(code)
        
        ticker = yf.Ticker(symbol)
        
        # 方法1: 尝试使用 fast_info 获取最新价格
        try:
            fast_info = ticker.fast_info
            last_price = fast_info.get('lastPrice') or fast_info.get('regularMarketPrice')
            
            if last_price and not pd.isna(last_price):
                beijing_time = get_beijing_time()
                today_str = beijing_time.strftime('%Y-%m-%d')
                
                print(f"[市场数据] [yfinance实时] 通过 fast_info 获取到实时价格: {last_price}")
                
                # 获取财务指标
                financial_indicators = fetch_financial_indicators_yfinance(ticker)
                
                # 构造 DataFrame
                data = {
                    'date': [today_str],
                    'open': [None],
                    'close': [float(last_price)],
                    'high': [fast_info.get('dayHigh') or None],
                    'low': [fast_info.get('dayLow') or None],
                    'volume': [fast_info.get('volume') or None],
                    'turnover': [None],
                    'amplitude': [None],
                    'change_pct': [None],
                    'change_amount': [None],
                    'turnover_rate': [None],
                    'pe_ratio': [financial_indicators['pe_ratio']],
                    'pb_ratio': [financial_indicators['pb_ratio']],
                    'market_cap': [financial_indicators['market_cap']],
                    'eps_forecast': [financial_indicators['eps_forecast']]
                }
                
                df = pd.DataFrame(data)
                print(f"[市场数据] [yfinance实时] 成功获取实时价格数据")
                return df
        except Exception as e:
            print(f"[市场数据] [yfinance实时] fast_info 获取失败: {str(e)}")
        
        # 方法2: 尝试使用 history(period='1d') 获取今天的数据
        try:
            df = ticker.history(period='1d')
            if df is not None and not df.empty:
                # 重置索引，将 Date 作为列
                df = df.reset_index()
                
                # 重命名列
                column_mapping = {
                    'Date': 'date',
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                }
                df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
                
                # 格式化日期为今天
                beijing_time = get_beijing_time()
                today_str = beijing_time.strftime('%Y-%m-%d')
                if 'date' in df.columns:
                    df['date'] = today_str
                
                # 添加缺失的列
                expected_cols = ['date', 'open', 'close', 'high', 'low', 'volume', 'turnover', 'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
                for col in expected_cols:
                    if col not in df.columns:
                        df[col] = None
                
                df = df[expected_cols]
                print(f"[市场数据] [yfinance实时] 通过 history(period='1d') 获取到实时数据")
                return df
        except Exception as e:
            print(f"[市场数据] [yfinance实时] history(period='1d') 获取失败: {str(e)}")
        
        return None
        
    except Exception as e:
        print(f"[市场数据] [yfinance实时] 获取实时价格失败: {type(e).__name__}: {str(e)}")
        return None


def standardize_market_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    expected_cols = ['date', 'open', 'close', 'high', 'low', 'volume', 'turnover', 'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None
    return df


def fetch_stock_data_akshare(code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    使用 AkShare 获取 A 股历史数据
    """
    if not AKSHARE_AVAILABLE:
        print("[市场数据] [akshare] 不可用")
        return None
    if not is_a_share_code(code):
        return None

    start_date = normalize_date_str(start_date)
    end_date = normalize_date_str(end_date)
    # 应用日期跨度补丁
    start_date, end_date = apply_date_span_patch(start_date, end_date)
    symbol = normalize_stock_code(code)

    try:
        print(f"[市场数据] [akshare] 获取A股数据: symbol={symbol}, start_date={start_date}, end_date={end_date}")
        df = ak.stock_zh_a_hist(symbol=symbol, start_date=start_date, end_date=end_date, adjust="qfq")
    except Exception as e:
        print(f"[市场数据] [akshare] 获取A股数据失败: {type(e).__name__}: {str(e)}")
        return None

    if df is None or df.empty:
        print("[市场数据] [akshare] A股数据为空")
        return None

    column_mapping = {
        '日期': 'date',
        '开盘': 'open',
        '收盘': 'close',
        '最高': 'high',
        '最低': 'low',
        '成交量': 'volume',
        '成交额': 'turnover',
        '涨跌幅': 'change_pct',
        '涨跌额': 'change_amount',
        '换手率': 'turnover_rate'
    }
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

    numeric_cols = ['open', 'close', 'high', 'low', 'volume', 'turnover', 'change_pct', 'change_amount', 'turnover_rate']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df = standardize_market_dataframe(df)
    print(f"[市场数据] [akshare] 成功获取 {len(df)} 条A股数据")
    return df


def resolve_futures_main_contract(code: str) -> Optional[str]:
    """
    解析期货主力合约代码（使用 ak.futures_main_relation 识别主力）
    输入格式：IF0, IF=F, CF.IF0, IC, IM0, IH 等
    输出：主力合约代码或指数代码（如 IF88 表示连续合约指数）
    """
    if not AKSHARE_AVAILABLE:
        return None

    # 清理代码格式：移除 CF., =F 等标记，移除尾部的 0
    code_upper = code.upper().strip()
    symbol = code_upper.replace("CF.", "").replace("=F", "").strip()
    
    # 移除尾部的 0（IF0 -> IF, IM0 -> IM）
    if symbol.endswith("0"):
        symbol = symbol[:-1]
    
    # 提取基础代码（IF, IC, IM, IH）
    base_symbol = None
    for prefix in ["IF", "IC", "IM", "IH"]:
        if symbol.startswith(prefix):
            base_symbol = prefix
            break
    
    if not base_symbol:
        print(f"[市场数据] [akshare] 无法识别期货代码: {code}")
        return None
    
    print(f"[市场数据] [akshare] 解析期货代码: 输入={code}, 基础代码={base_symbol}")
    
    # 尝试使用 futures_main_relation 获取主力合约
    try:
        # 获取主力合约关系表
        main_relation_df = ak.futures_main_relation(symbol=base_symbol)
        if main_relation_df is not None and not main_relation_df.empty:
            # 尝试获取主力合约代码
            # 主力合约关系表通常包含 'symbol', 'main_contract' 等列
            # 获取最新的主力合约
            if 'main_contract' in main_relation_df.columns:
                main_contract = main_relation_df['main_contract'].iloc[-1]
                if main_contract:
                    print(f"[市场数据] [akshare] 通过 futures_main_relation 获取主力合约: {main_contract}")
                    return main_contract
            elif '合约' in main_relation_df.columns:
                main_contract = main_relation_df['合约'].iloc[-1]
                if main_contract:
                    print(f"[市场数据] [akshare] 通过 futures_main_relation 获取主力合约: {main_contract}")
                    return main_contract
    except Exception as e:
        print(f"[市场数据] [akshare] futures_main_relation 获取失败，使用备用映射: {str(e)}")
    
    # 备用方案：使用连续合约代码映射
    # 88 表示加权连续合约，89 表示近月连续合约
    index_mapping = {
        "IF": "IF88",  # 沪深300股指期货连续合约
        "IC": "IC88",  # 中证500股指期货连续合约
        "IH": "IH88",  # 上证50股指期货连续合约
        "IM": "IM88",  # 中证1000股指期货连续合约
    }
    
    if base_symbol in index_mapping:
        main_contract = index_mapping[base_symbol]
        print(f"[市场数据] [akshare] 使用连续合约（备用方案）: {main_contract}")
        return main_contract
    
    print(f"[市场数据] [akshare] 未找到映射: symbol={base_symbol}")
    return None


def fetch_futures_data_akshare(code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    使用 AkShare 获取股指期货主力合约历史数据
    支持格式：IF0, IC, IM0, IH, CF.IF0, IF=F 等
    """
    if not AKSHARE_AVAILABLE:
        print("[市场数据] [akshare] 不可用")
        return None
    if not is_futures_main_code(code):
        print(f"[市场数据] [akshare] 非期货代码: {code}")
        return None

    start_date = normalize_date_str(start_date)
    end_date = normalize_date_str(end_date)
    # 应用日期跨度补丁
    start_date, end_date = apply_date_span_patch(start_date, end_date)

    main_contract = resolve_futures_main_contract(code)
    if not main_contract:
        print(f"[市场数据] [akshare] 未找到主力合约: code={code}")
        return None

    try:
        print(f"[市场数据] [akshare] 获取期货数据: code={code}, main_contract={main_contract}, start_date={start_date}, end_date={end_date}")
        
        # 尝试多种 API 获取期货数据
        df = None
        
        # 方法1: 使用 futures_zh_daily_sina（最稳定，支持连续合约）
        try:
            # 将日期格式转换为 YYYYMMDD（akshare 期货接口要求）
            start_dt = start_date.replace("-", "")
            end_dt = end_date.replace("-", "")
            df = ak.futures_zh_daily_sina(symbol=main_contract, start_date=start_dt, end_date=end_dt)
            if df is not None and not df.empty:
                print(f"[市场数据] [akshare] 使用 futures_zh_daily_sina 成功")
        except Exception as e:
            print(f"[市场数据] [akshare] futures_zh_daily_sina 失败: {str(e)}")
        
        # 方法2: 如果方法1失败，尝试 get_cffex_daily（中金所接口）
        if df is None or df.empty:
            try:
                df = ak.get_cffex_daily(date=end_date.replace("-", ""))
                if df is not None and not df.empty:
                    # 过滤出对应的合约
                    base_symbol = main_contract[:2]  # IF88 -> IF
                    df = df[df['symbol'].str.startswith(base_symbol)]
                    if not df.empty:
                        print(f"[市场数据] [akshare] 使用 get_cffex_daily 成功")
            except Exception as e:
                print(f"[市场数据] [akshare] get_cffex_daily 失败: {str(e)}")
        
    except Exception as e:
        print(f"[市场数据] [akshare] 获取期货数据失败: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        return None

    if df is None or df.empty:
        print(f"[市场数据] [akshare] 期货数据为空: main_contract={main_contract}")
        return None

    print(f"[市场数据] [akshare] 原始数据列: {df.columns.tolist()}")
    
    # 映射多种可能的列名
    column_mapping = {
        'date': 'date',
        '日期': 'date',
        'Date': 'date',
        '开盘': 'open',
        'open': 'open',
        'Open': 'open',
        '收盘': 'close',
        'close': 'close',
        'Close': 'close',
        '最高': 'high',
        'high': 'high',
        'High': 'high',
        '最低': 'low',
        'low': 'low',
        'Low': 'low',
        '成交量': 'volume',
        'volume': 'volume',
        'Volume': 'volume',
        '成交额': 'turnover',
        'turnover': 'turnover',
        'Turnover': 'turnover'
    }
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

    numeric_cols = ['open', 'close', 'high', 'low', 'volume', 'turnover']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df = standardize_market_dataframe(df)
    print(f"[市场数据] [akshare] 成功获取 {len(df)} 条期货数据")
    return df


def fetch_cached_market_data(code: str, start_date: str, end_date: str, db: Session) -> Optional[pd.DataFrame]:
    if db is None:
        return None

    start_date = normalize_date_str(start_date)
    end_date = normalize_date_str(end_date)

    asset = db.query(Asset).filter(Asset.code == code).first()
    if not asset and is_a_share_code(code):
        clean_code = normalize_stock_code(code)
        asset = db.query(Asset).filter(Asset.code.like(f"%{clean_code}%")).first()
    if not asset:
        return None

    try:
        start_obj = date.fromisoformat(start_date)
        end_obj = date.fromisoformat(end_date)
    except ValueError:
        return None

    records = db.query(MarketData).filter(
        MarketData.asset_id == asset.id,
        MarketData.date >= start_obj,
        MarketData.date <= end_obj
    ).order_by(MarketData.date.asc()).all()

    if not records:
        return None

    data = {
        'date': [r.date.strftime('%Y-%m-%d') for r in records],
        'open': [None for _ in records],
        'close': [r.close_price for r in records],
        'high': [None for _ in records],
        'low': [None for _ in records],
        'volume': [r.volume for r in records],
        'turnover': [None for _ in records],
        'amplitude': [None for _ in records],
        'change_pct': [None for _ in records],
        'change_amount': [None for _ in records],
        'turnover_rate': [r.turnover_rate for r in records],
        'pe_ratio': [r.pe_ratio for r in records],
        'pb_ratio': [r.pb_ratio for r in records],
        'market_cap': [r.market_cap for r in records],
        'eps_forecast': [r.eps_forecast for r in records]
    }

    df = pd.DataFrame(data)
    df = standardize_market_dataframe(df)
    print(f"[市场数据] [缓存] 使用数据库缓存数据: code={code}, 条数={len(df)}")
    return df


def fetch_stock_data_yfinance(code: str, start_date: str, end_date: str, use_realtime: bool = False) -> Optional[pd.DataFrame]:
    """
    使用 yfinance 获取A股股票数据（主数据源）
    
    Args:
        code: 股票代码（支持多种格式）
        start_date: 开始日期 "YYYY-MM-DD"
        end_date: 结束日期 "YYYY-MM-DD"
        use_realtime: 是否尝试获取实时价格（盘中交易时间）
    
    Returns:
        pd.DataFrame 或 None（失败时）
    """
    if not YFINANCE_AVAILABLE:
        print(f"[市场数据] yfinance 不可用")
        return None
    
    try:
        start_date = normalize_date_str(start_date)
        end_date = normalize_date_str(end_date)
        # 应用日期跨度补丁
        start_date, end_date = apply_date_span_patch(start_date, end_date)
        print(f"[市场数据] [yfinance] 尝试获取数据: code={code}, start_date={start_date}, end_date={end_date}, use_realtime={use_realtime}")
        
        # 如果是盘中且需要实时数据，且查询的是今天的数据
        beijing_time = get_beijing_time()
        today_str = beijing_time.strftime('%Y-%m-%d')
        
        if use_realtime and is_trading_hours() and end_date >= today_str:
            print(f"[市场数据] [yfinance] 盘中交易时间，尝试获取实时价格")
            realtime_df = fetch_realtime_price_yfinance(code)
            if realtime_df is not None and not realtime_df.empty:
                print(f"[市场数据] [yfinance] 成功获取实时价格数据")
                return realtime_df
        
        # 转换为 yfinance 格式
        symbol = convert_to_yfinance_symbol(code)
        print(f"[市场数据] [yfinance] 转换后的符号: {symbol}")
        
        ticker = yf.Ticker(symbol)
        
        # 优先尝试使用 fast_info 获取实时价格（特别是查询今天的数据时）
        if end_date >= today_str:
            try:
                fast_info = ticker.fast_info
                last_price = fast_info.get('lastPrice') or fast_info.get('regularMarketPrice') or fast_info.get('previousClose')
                
                if last_price and not pd.isna(last_price):
                    print(f"[市场数据] [yfinance] 成功获取实时价格: {last_price}")
                    
                    # 获取财务指标
                    financial_indicators = fetch_financial_indicators_yfinance(ticker)
                    
                    # 构造 DataFrame
                    data = {
                        'date': [today_str],
                        'open': [fast_info.get('open') or fast_info.get('previousClose') or None],
                        'close': [float(last_price)],
                        'high': [fast_info.get('dayHigh') or fast_info.get('regularMarketDayHigh') or None],
                        'low': [fast_info.get('dayLow') or fast_info.get('regularMarketDayLow') or None],
                        'volume': [fast_info.get('volume') or fast_info.get('regularMarketVolume') or None],
                        'turnover': [None],
                        'amplitude': [None],
                        'change_pct': [None],
                        'change_amount': [None],
                        'turnover_rate': [None],
                        'pe_ratio': [financial_indicators['pe_ratio']],
                        'pb_ratio': [financial_indicators['pb_ratio']],
                        'market_cap': [financial_indicators['market_cap']],
                        'eps_forecast': [financial_indicators['eps_forecast']]
                    }
                    
                    df = pd.DataFrame(data)
                    print(f"[市场数据] [yfinance] 使用 fast_info 数据，日期: {today_str}")
                    return df
            except AttributeError as e:
                # fast_info 在某些环境下可能不存在
                print(f"[市场数据] [yfinance] fast_info 不可用: {str(e)}，降级使用 history()")
            except Exception as e:
                print(f"[市场数据] [yfinance] fast_info 获取失败: {type(e).__name__}: {str(e)}，降级使用 history()")
        
        # 降级使用 history() 方法
        try:
            df = ticker.history(start=start_date, end=end_date)
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            if is_yfinance_rate_limit_error(e):
                print(f"[市场数据] [yfinance] 触发频率限制: {error_msg}")
                raise YFinanceRateLimitError(error_msg) from e
            # 检查是否是超时或网络相关错误
            if 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower():
                print(f"[市场数据] [yfinance] 获取数据超时: {error_msg}")
            elif 'connection' in error_msg.lower() or 'socket' in error_msg.lower():
                print(f"[市场数据] [yfinance] 网络连接错误: {error_msg}")
            else:
                print(f"[市场数据] [yfinance] 获取数据时发生异常: {error_type}: {error_msg}")
            return None
        
        if df is None or df.empty:
            print(f"[市场数据] [yfinance] history() 未获取到数据")
            return None
        
        print(f"[市场数据] [yfinance] 成功获取 {len(df)} 条数据")
        
        # 重置索引，将 Date 作为列
        df = df.reset_index()
        
        # 重命名列
        column_mapping = {
            'Date': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }
        
        # 只重命名存在的列
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        # 格式化日期
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        # 添加缺失的列（使用默认值）
        expected_cols = ['date', 'open', 'close', 'high', 'low', 'volume', 'turnover', 'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None
        
        # 确保列顺序正确
        df = df[expected_cols]
        
        # 获取财务指标（PE, PB, 市值, EPS预测）
        try:
            financial_indicators = fetch_financial_indicators_yfinance(ticker)
            # 将财务指标添加到每一行（因为财务指标是当前值，不是历史值）
            for key, value in financial_indicators.items():
                df[key] = value
        except Exception as e:
            print(f"[市场数据] [yfinance] 获取财务指标时发生异常: {type(e).__name__}: {str(e)}")
            # 即使财务指标获取失败，也继续返回历史数据
            # 设置默认值
            df['pe_ratio'] = 0.0
            df['pb_ratio'] = 0.0
            df['market_cap'] = 0.0
            df['eps_forecast'] = 0.0
        
        print(f"[市场数据] [yfinance] 数据处理完成")
        return df
        
    except Exception as e:
        print(f"[市场数据] [yfinance] 获取数据失败: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        return None


def fetch_stock_data_baostock(code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    使用 baostock 获取A股股票数据（备份数据源）
    
    Args:
        code: 股票代码（支持多种格式）
        start_date: 开始日期 "YYYY-MM-DD"
        end_date: 结束日期 "YYYY-MM-DD"
    
    Returns:
        pd.DataFrame 或 None（失败时）
    """
    if not BAOSTOCK_AVAILABLE:
        print(f"[市场数据] [baostock] 不可用")
        return None
    
    try:
        print(f"[市场数据] [baostock] 尝试获取数据: code={code}")
        
        # 标准化代码
        clean_code = normalize_stock_code(code)
        
        # 转换为 baostock 格式（需要添加市场前缀）
        if clean_code.startswith('6'):
            bs_code = f"sh.{clean_code}"  # 上海市场
        elif clean_code.startswith(('0', '3')):
            bs_code = f"sz.{clean_code}"  # 深圳市场
        else:
            print(f"[市场数据] [baostock] 无法识别代码 {clean_code} 的市场")
            return None
        
        print(f"[市场数据] [baostock] 转换后的代码: {bs_code}")
        
        # 登录 baostock
        lg = bs.login()
        if lg.error_code != '0':
            print(f"[市场数据] [baostock] 登录失败: {lg.error_msg}")
            return None
        
        try:
            # 统一日期格式（YYYY-MM-DD），避免错误转成 20260103
            try:
                start_dt = format_date_for_baostock(start_date)
                end_dt = format_date_for_baostock(end_date)
                print(f"[市场数据] [baostock] 格式化后的日期: start_date={start_dt}, end_date={end_dt} (原始输入: start_date={start_date}, end_date={end_date})")
            except ValueError as e:
                print(f"[市场数据] [baostock] 日期格式错误: {str(e)}")
                traceback.print_exc()
                return None
            except Exception as e:
                print(f"[市场数据] [baostock] 日期格式化时发生未预期的异常: {type(e).__name__}: {str(e)}")
                traceback.print_exc()
                return None
            
            # 获取数据（添加异常捕获，防止网络错误导致崩溃）
            try:
                rs = bs.query_history_k_data_plus(
                    bs_code,
                    "date,open,high,low,close,preclose,volume,amount,adjustflag,turn,pctChg,isST",
                    start_date=start_dt,
                    end_date=end_dt,
                    frequency="d",
                    adjustflag="3"  # 前复权
                )
            except ValueError as e:
                print(f"[市场数据] [baostock] 值错误（可能是日期格式问题）: {str(e)}")
                traceback.print_exc()
                return None
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                # 检查是否是超时或网络相关错误
                if 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower():
                    print(f"[市场数据] [baostock] 查询超时: {error_msg}")
                elif 'connection' in error_msg.lower() or 'socket' in error_msg.lower():
                    print(f"[市场数据] [baostock] 网络连接错误: {error_msg}")
                else:
                    print(f"[市场数据] [baostock] 查询时发生异常: {error_type}: {error_msg}")
                traceback.print_exc()
                return None
            
            # 检查 rs 是否为 None
            if rs is None:
                print(f"[市场数据] [baostock] 查询返回 None，可能网络错误或服务异常")
                beijing_time = get_beijing_time()
                today_str = beijing_time.strftime('%Y-%m-%d')
                # 检查是否是查询今天的数据
                end_date_clean = str(end_date).replace("-", "") if isinstance(end_date, str) else end_date.strftime('%Y%m%d')
                today_clean = today_str.replace("-", "")
                if end_date_clean == today_clean:
                    print(f"[市场数据] [baostock] 当前时间点 Baostock 暂无收盘数据，尝试回退或保留实时价")
                return None
            
            if rs.error_code != '0':
                error_msg = rs.error_msg if hasattr(rs, 'error_msg') else '未知错误'
                print(f"[市场数据] [baostock] 查询失败: error_code={rs.error_code}, error_msg={error_msg}")
                
                # 如果是日期格式错误，打印更详细的信息
                if '日期格式' in error_msg or '日期格式不正确' in error_msg or '日期格式错误' in error_msg.lower():
                    print(f"[市场数据] [baostock] 日期格式错误详情: start_date={start_dt}, end_date={end_dt}")
                    print(f"[市场数据] [baostock] 原始输入: start_date={start_date}, end_date={end_date}")
                    print(f"[市场数据] [baostock] 日期类型: start_date类型={type(start_date)}, end_date类型={type(end_date)}")
                
                return None
            
            # 转换为 DataFrame
            data_list = []
            try:
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())
            except Exception as e:
                print(f"[市场数据] [baostock] 读取数据时发生异常: {type(e).__name__}: {str(e)}")
                # 如果已经有部分数据，继续处理
                if not data_list:
                    return None
            
            if not data_list:
                print(f"[市场数据] [baostock] 未获取到数据")
                return None
            
            # 创建 DataFrame
            df = pd.DataFrame(data_list, columns=rs.fields)
            
            # 重命名列
            column_mapping = {
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'turn': 'turnover_rate',
                'pctChg': 'change_pct'
            }
            
            df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
            
            # 转换数据类型
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'turnover_rate', 'change_pct']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 添加缺失的列
            expected_cols = ['date', 'open', 'close', 'high', 'low', 'volume', 'turnover', 'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = None
            
            # 计算 change_amount（如果有 close 和 change_pct）
            if 'close' in df.columns and 'change_pct' in df.columns:
                df['change_amount'] = df['close'] * df['change_pct'] / 100
            
            # 确保列顺序正确
            df = df[expected_cols]
            
            print(f"[市场数据] [baostock] 成功获取 {len(df)} 条数据")
            return df
            
        finally:
            # 登出 baostock
            bs.logout()
        
    except Exception as e:
        print(f"[市场数据] [baostock] 获取数据失败: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        # 确保登出
        try:
            bs.logout()
        except:
            pass
        return None


def fetch_stock_data_with_fallback(code: str, target_date: date, db: Session) -> Optional[pd.DataFrame]:
    """
    获取股票数据，带回退机制：如果今天的数据获取不到，回溯最近一个交易日
    
    Args:
        code: 股票代码
        target_date: 目标日期
        db: 数据库会话
    
    Returns:
        pd.DataFrame 或 None
    """
    try:
        beijing_time = get_beijing_time()
        today = beijing_time.date()
        target_date_str = normalize_date_str(target_date)
        
        # 判断是否在交易时间内
        in_trading_hours = is_trading_hours()
        
        print(f"[市场数据] [回退机制] 尝试获取数据: code={code}, target_date={target_date_str}, 当前时间={'盘中' if in_trading_hours else '盘后'}")
        
        # 如果是今天且在交易时间内，尝试获取实时数据
        if target_date == today and in_trading_hours:
            print(f"[市场数据] [回退机制] 盘中交易时间，优先获取实时价格")
            try:
                # 尝试 yfinance 实时价格
                df = fetch_stock_data_yfinance(code, target_date_str, target_date_str, use_realtime=True)
                if df is not None and not df.empty:
                    print(f"[市场数据] [回退机制] 成功获取实时价格")
                    return df
            except Exception as e:
                print(f"[市场数据] [回退机制] 获取实时价格时发生异常: {type(e).__name__}: {str(e)}")
                # 继续尝试其他方法
        
        # 尝试获取目标日期的收盘数据
        print(f"[市场数据] [回退机制] 尝试获取目标日期 {target_date_str} 的收盘数据")
        try:
            df = fetch_stock_data(code, target_date_str, target_date_str)
            if df is not None and not df.empty:
                print(f"[市场数据] [回退机制] 成功获取目标日期数据")
                return df
        except Exception as e:
            print(f"[市场数据] [回退机制] 获取目标日期数据时发生异常: {type(e).__name__}: {str(e)}")
            traceback.print_exc()
            # 继续尝试回退机制
        
        # 如果目标日期是今天且获取失败，尝试回溯最近交易日
        if target_date == today:
            print(f"[市场数据] [回退机制] 今天的数据获取失败，开始回溯最近交易日...")
            
            # 从数据库中查找最近有数据的交易日
            from database.models import Asset, MarketData
            try:
                asset = db.query(Asset).filter(Asset.code.like(f"%{normalize_stock_code(code)}%")).first()
                if asset:
                    latest_data = db.query(MarketData).filter(
                        MarketData.asset_id == asset.id,
                        MarketData.date < today
                    ).order_by(MarketData.date.desc()).first()
                    
                    if latest_data:
                        fallback_date = latest_data.date
                        print(f"[市场数据] [回退机制] 找到最近交易日: {fallback_date}")
                        
                        # 直接使用数据库中的数据，而不是再次调用外部 API
                        # 构造 DataFrame 从数据库数据
                        data = {
                            'date': [target_date_str],  # 使用目标日期（今天）
                            'open': [latest_data.close_price],  # 使用收盘价作为开盘价
                            'close': [latest_data.close_price],
                            'high': [latest_data.close_price],
                            'low': [latest_data.close_price],
                            'volume': [latest_data.volume] if latest_data.volume else [None],
                            'turnover': [None],
                            'amplitude': [None],
                            'change_pct': [None],
                            'change_amount': [None],
                            'turnover_rate': [latest_data.turnover_rate] if latest_data.turnover_rate else [None]
                        }
                        
                        df = pd.DataFrame(data)
                        print(f"[市场数据] [回退机制] 使用数据库中的最近交易日 {fallback_date} 的数据作为回退")
                        return df
            except Exception as e:
                print(f"[市场数据] [回退机制] 查询数据库时发生异常: {type(e).__name__}: {str(e)}")
                traceback.print_exc()
            
            # 如果数据库中没有数据，尝试回溯日期（最多回溯5天，防止无限回溯导致崩溃）
            MAX_BACKTRACK_DAYS = 5
            print(f"[市场数据] [回退机制] 数据库中没有找到数据，尝试从外部API回溯（最多{MAX_BACKTRACK_DAYS}天）...")
            for days_back in range(1, MAX_BACKTRACK_DAYS + 1):
                fallback_date = today - timedelta(days=days_back)
                fallback_date_str = normalize_date_str(fallback_date)
                
                print(f"[市场数据] [回退机制] 尝试回溯 {days_back}/{MAX_BACKTRACK_DAYS} 天: {fallback_date_str}")
                try:
                    df = fetch_stock_data(code, fallback_date_str, fallback_date_str)
                    if df is not None and not df.empty:
                        # 将日期更新为今天
                        df['date'] = target_date_str
                        print(f"[市场数据] [回退机制] 使用 {fallback_date_str} 的数据作为回退")
                        return df
                except Exception as e:
                    print(f"[市场数据] [回退机制] 回溯 {fallback_date_str} 时发生异常: {type(e).__name__}: {str(e)}")
                    continue
            
            print(f"[市场数据] [回退机制] 已回溯 {MAX_BACKTRACK_DAYS} 天仍无数据，停止回溯以防止崩溃")
            
            print(f"[市场数据] [回退机制] 所有尝试都失败，无法获取数据")
            return None
    except Exception as e:
        print(f"[市场数据] [回退机制] 执行回退机制时发生未预期的异常: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        return None


def fetch_stock_data(code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    获取A股股票数据（主数据源：yfinance，备份：baostock）
    
    Args:
        code: 股票代码，支持多种格式
        start_date: 开始日期 "YYYY-MM-DD"
        end_date: 结束日期 "YYYY-MM-DD"
    
    Returns:
        pd.DataFrame 或 None（所有数据源都失败时）
    """
    start_date = normalize_date_str(start_date)
    end_date = normalize_date_str(end_date)
    print(f"[市场数据] 开始获取股票数据: code={code}, start_date={start_date}, end_date={end_date}")
    
    beijing_time = get_beijing_time()
    today_str = beijing_time.strftime('%Y-%m-%d')
    in_trading_hours = is_trading_hours()
    
    # 期货主力合约（CF. 前缀）
    if is_futures_main_code(code):
        df = fetch_futures_data_akshare(code, start_date, end_date)
        if df is not None and not df.empty:
            print(f"[市场数据] 使用 AkShare 期货数据成功获取")
            return df

    # A股优先使用 AkShare（避免 yfinance 限频）
    if is_a_share_code(code):
        df = fetch_stock_data_akshare(code, start_date, end_date)
        if df is not None and not df.empty:
            print(f"[市场数据] 使用 AkShare A股数据成功获取")
            return df

    # 如果查询的是今天的数据且在交易时间内，尝试获取实时价格
    if end_date >= today_str and in_trading_hours and not is_futures_main_code(code):
        print(f"[市场数据] 盘中交易时间，尝试获取实时价格")
        df = fetch_stock_data_yfinance(code, start_date, end_date, use_realtime=True)
        if df is not None and not df.empty:
            print(f"[市场数据] 使用 yfinance 实时价格成功获取数据")
            return df
    
    # 1. 优先尝试 yfinance（收盘数据）
    try:
        df = fetch_stock_data_yfinance(code, start_date, end_date, use_realtime=False)
        if df is not None and not df.empty:
            print(f"[市场数据] 使用 yfinance 成功获取数据")
            return df
    except YFinanceRateLimitError as e:
        print(f"[市场数据] yfinance 触发限频: {str(e)}")
        if is_domestic_code(code):
            df = fetch_stock_data_akshare(code, start_date, end_date)
            if df is not None and not df.empty:
                print(f"[市场数据] 降级到 AkShare 成功获取数据")
                return df
        raise
    
    # 2. yfinance 失败，尝试 baostock
    if is_a_share_code(code):
        print(f"[市场数据] yfinance 未获取到数据，尝试 baostock 备份...")
        df = fetch_stock_data_baostock(code, start_date, end_date)
        if df is not None and not df.empty:
            print(f"[市场数据] 使用 baostock 成功获取数据")
            return df
    
    # 3. 所有数据源都失败
    print(f"[市场数据] 所有数据源都未获取到数据")
    return None


def fetch_fund_data(code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    获取基金/ETF数据（强制使用 AkShare）
    
    接口适配策略：
    1. 如果是6位数字代码（如 518880），先尝试 ak.fund_etf_hist_sina 获取场内数据
    2. 若失败，则尝试 ak.fund_open_fund_info_em 获取净值数据
    
    Args:
        code: 基金代码
        start_date: 开始日期 "YYYY-MM-DD"
        end_date: 结束日期 "YYYY-MM-DD"
    
    Returns:
        pd.DataFrame 或 None（失败时）
    """
    if not AKSHARE_AVAILABLE:
        print(f"[市场数据] [基金] AkShare 不可用，无法获取基金数据")
        return None
    
    start_date = normalize_date_str(start_date)
    end_date = normalize_date_str(end_date)
    # 应用日期跨度补丁
    start_date, end_date = apply_date_span_patch(start_date, end_date)
    
    print(f"[市场数据] [基金] 开始获取基金数据: code={code}, start_date={start_date}, end_date={end_date}")
    
    # 标准化代码（去除前缀后缀）
    normalized_code = normalize_stock_code(code)
    
    # 判断是否为6位数字代码
    is_six_digit = len(normalized_code) == 6 and normalized_code.isdigit()
    
    df = None
    
    # 策略1: 如果是6位数字代码，先尝试场内ETF数据
    if is_six_digit:
        print(f"[市场数据] [基金] 检测到6位数字代码，先尝试场内ETF数据接口")
        try:
            # 使用 ak.fund_etf_hist_sina 获取场内ETF数据
            # 该函数只接受基金代码作为位置参数，返回所有历史数据
            # 注意：根据 AkShare 最新版本，该函数只接受位置参数，不接受关键字参数
            df = ak.fund_etf_hist_sina(normalized_code)
            
            if df is not None and not df.empty:
                # 标准化列名
                column_mapping = {
                    'date': 'date',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume'
                }
                # 重命名列（如果存在）
                for old_col, new_col in column_mapping.items():
                    if old_col in df.columns:
                        df = df.rename(columns={old_col: new_col})
                
                # 确保日期格式正确
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                
                # 过滤日期范围
                if 'date' in df.columns:
                    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                
                if df is not None and not df.empty:
                    print(f"[市场数据] [基金] 场内ETF数据获取成功: {len(df)} 条")
                    # 添加缺失的列
                    expected_cols = ['date', 'open', 'close', 'high', 'low', 'volume', 'turnover', 'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
                    for col in expected_cols:
                        if col not in df.columns:
                            df[col] = None
                    df = df[expected_cols] if all(col in df.columns for col in expected_cols) else df
                    return df
        except Exception as e:
            print(f"[市场数据] [基金] 场内ETF数据获取失败: {type(e).__name__}: {str(e)}")
            df = None
    
    # 策略2: 尝试净值数据接口（场内失败或非6位代码）
    if df is None or df.empty:
        print(f"[市场数据] [基金] 尝试净值数据接口")
        try:
            # 使用 ak.fund_open_fund_info_em 获取基金净值数据
            # 根据 AkShare 最新版本，尝试使用 symbol 参数（如果失败则使用位置参数）
            # indicator 可选值："单位净值走势", "累计净值走势", "累计收益率走势", "同类排名走势", "同类平均走势"
            try:
                df = ak.fund_open_fund_info_em(symbol=normalized_code, indicator="单位净值走势")
            except TypeError:
                # 如果 symbol 参数失败，尝试位置参数
                df = ak.fund_open_fund_info_em(normalized_code, "单位净值走势")
            
            if df is not None and not df.empty:
                print(f"[市场数据] [基金] 获取到原始数据 {len(df)} 条，列名: {df.columns.tolist()}")
                
                # 立即执行字段重命名（根据 AkShare 实际返回的列名）
                # 可能的列名：净值日期、日期、单位净值、净值等
                if '净值日期' in df.columns:
                    df = df.rename(columns={'净值日期': 'date'})
                elif '日期' in df.columns:
                    df = df.rename(columns={'日期': 'date'})
                
                if '单位净值' in df.columns:
                    df = df.rename(columns={'单位净值': 'close'})
                elif '净值' in df.columns:
                    df = df.rename(columns={'净值': 'close'})
                
                # 确保日期格式正确
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                    # 强制执行日期过滤（接口返回全量数据，必须过滤）
                    print(f"[市场数据] [基金] 执行日期过滤: {start_date} 至 {end_date}")
                    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                    print(f"[市场数据] [基金] 过滤后数据: {len(df)} 条")
                
                if df is not None and not df.empty:
                    # 净值数据通常只有日期和净值，需要补充其他字段
                    if 'close' in df.columns:
                        # 使用净值作为收盘价
                        if 'open' not in df.columns:
                            df['open'] = df['close']  # 净值数据通常没有开盘价，使用净值代替
                        if 'high' not in df.columns:
                            df['high'] = df['close']
                        if 'low' not in df.columns:
                            df['low'] = df['close']
                        if 'volume' not in df.columns:
                            df['volume'] = None
                    
                    print(f"[市场数据] [基金] 净值数据获取成功: {len(df)} 条")
                    # 添加缺失的列
                    expected_cols = ['date', 'open', 'close', 'high', 'low', 'volume', 'turnover', 'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
                    for col in expected_cols:
                        if col not in df.columns:
                            df[col] = None
                    df = df[expected_cols] if all(col in df.columns for col in expected_cols) else df
                    return df
        except Exception as e:
            print(f"[市场数据] [基金] 净值数据获取失败: {type(e).__name__}: {str(e)}")
            traceback.print_exc()
            df = None
    
    print(f"[市场数据] [基金] 所有接口均失败，无法获取基金数据")
    return None


def parse_market_data(df: pd.DataFrame, asset_type: str, code: str) -> List[Dict]:
    """
    解析市场数据为标准化格式
    
    Returns:
        list of dicts: [{date, close_price, volume, turnover_rate, ...}]
    """
    if df is None or df.empty:
        return []
    
    results = []
    try:
        for _, row in df.iterrows():
            data = {
                "date": None,
                "close_price": None,
                "volume": None,
                "turnover_rate": None,
                "pe_ratio": None,
                "pb_ratio": None,
                "market_cap": None,
                "eps_forecast": None,
                "additional_data": {}
            }
            
            # 处理日期
            if 'date' in row:
                if isinstance(row['date'], str):
                    try:
                        data["date"] = normalize_date_str(row['date'])
                    except ValueError:
                        data["date"] = row['date']
                elif isinstance(row['date'], (int, np.integer)):
                    try:
                        data["date"] = normalize_date_str(str(row['date']))
                    except ValueError:
                        data["date"] = str(row['date'])
                elif hasattr(row['date'], 'date'):
                    data["date"] = row['date'].date().isoformat()
                elif hasattr(row['date'], 'strftime'):
                    data["date"] = row['date'].strftime("%Y-%m-%d")
            
            # 处理收盘价
            if 'close' in row:
                try:
                    data["close_price"] = float(row['close'])
                except (ValueError, TypeError):
                    pass
            elif '净值' in row:
                try:
                    data["close_price"] = float(row['净值'])
                except (ValueError, TypeError):
                    pass
            
            # 处理成交量
            if 'volume' in row:
                try:
                    val = row['volume']
                    if pd.notna(val) and val is not None:
                        data["volume"] = float(val)
                except (ValueError, TypeError):
                    pass
            
            # 处理换手率
            if 'turnover_rate' in row:
                try:
                    val = row['turnover_rate']
                    if pd.notna(val) and val is not None:
                        data["turnover_rate"] = float(val)
                except (ValueError, TypeError):
                    pass
            
            # 处理市盈率 - 即使值为 0 也要提取（0 可能是真实值）
            if 'pe_ratio' in row:
                try:
                    val = row['pe_ratio']
                    if pd.notna(val) and val is not None:
                        data["pe_ratio"] = float(val)
                    # 即使值为 0，也明确设置为 0（而不是 None）
                    elif val == 0 or val == 0.0:
                        data["pe_ratio"] = 0.0
                except (ValueError, TypeError):
                    pass
            
            # 处理市净率 - 即使值为 0 也要提取
            if 'pb_ratio' in row:
                try:
                    val = row['pb_ratio']
                    if pd.notna(val) and val is not None:
                        data["pb_ratio"] = float(val)
                    elif val == 0 or val == 0.0:
                        data["pb_ratio"] = 0.0
                except (ValueError, TypeError):
                    pass
            
            # 处理总市值 - 即使值为 0 也要提取
            if 'market_cap' in row:
                try:
                    val = row['market_cap']
                    if pd.notna(val) and val is not None:
                        data["market_cap"] = float(val)
                    elif val == 0 or val == 0.0:
                        data["market_cap"] = 0.0
                except (ValueError, TypeError):
                    pass
            
            # 处理EPS预测 - 即使值为 0 也要提取
            if 'eps_forecast' in row:
                try:
                    val = row['eps_forecast']
                    if pd.notna(val) and val is not None:
                        data["eps_forecast"] = float(val)
                    elif val == 0 or val == 0.0:
                        data["eps_forecast"] = 0.0
                except (ValueError, TypeError):
                    pass
            
            # 其他数据存入additional_data
            for col in df.columns:
                if col not in ['date', 'close', '净值', 'close_price', 'volume', 'turnover_rate', '换手率', 'pe_ratio', 'pb_ratio', 'market_cap', 'eps_forecast']:
                    if pd.notna(row[col]) and row[col] is not None:
                        try:
                            data["additional_data"][col] = float(row[col]) if isinstance(row[col], (int, float)) else str(row[col])
                        except:
                            pass
            
            if data["date"] and data["close_price"] is not None:
                results.append(data)
    except Exception as e:
        print(f"[市场数据] 解析市场数据时出错: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
    
    return results


def apply_date_span_patch(start_date: str, end_date: str) -> tuple[str, str]:
    """
    日期跨度补丁：如果 start_date == end_date，自动将 end_date 延长一天
    
    Args:
        start_date: 开始日期 "YYYY-MM-DD"
        end_date: 结束日期 "YYYY-MM-DD"
    
    Returns:
        (start_date, end_date): 处理后的日期对
    """
    if start_date == end_date:
        from datetime import datetime, timedelta
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        end_date_patched = end_date_obj.strftime('%Y-%m-%d')
        print(f"[市场数据] [日期补丁] start_date == end_date ({start_date})，自动延长 end_date 至 {end_date_patched}")
        return start_date, end_date_patched
    return start_date, end_date


def fetch_asset_data(
    code: str,
    asset_type: str,
    start_date: str,
    end_date: str,
    db: Optional[Session] = None
) -> List[Dict]:
    """
    获取资产数据（统一接口 - 重构后的路由逻辑）
    
    路由策略：
    - Stock/ETF (asset_type == 'stock'): 使用 yfinance，国内代码强制转换后缀（.SS/.SZ）
    - Futures (asset_type == 'futures'): 强制使用 AkShare，通过 futures_main_relation 识别主力
    
    Args:
        code: 资产代码（支持多种格式：SH601727, 601727.SH, 601727 等）
        asset_type: 资产类型 (stock, fund, futures, forex)
        start_date: 开始日期 "YYYY-MM-DD"
        end_date: 结束日期 "YYYY-MM-DD"
        db: 数据库会话（用于回退机制，可选）
    
    Returns:
        list of market data dicts（失败时返回空列表）
    """
    print(f"[市场数据] ===== 开始获取资产数据 =====")
    print(f"[市场数据] 资产代码: {code}")
    print(f"[市场数据] 资产类型: {asset_type}")
    try:
        start_date = normalize_date_str(start_date)
        end_date = normalize_date_str(end_date)
        # 应用日期跨度补丁
        start_date, end_date = apply_date_span_patch(start_date, end_date)
    except ValueError as e:
        print(f"[市场数据] 错误: 无法解析日期范围: {str(e)}")
        return []
    print(f"[市场数据] 日期范围: {start_date} 至 {end_date}")
    
    try:
        df = None
        beijing_time = get_beijing_time()
        today = beijing_time.date()
        
        # 安全地解析日期
        try:
            if isinstance(end_date, str):
                end_date_obj = date.fromisoformat(end_date)
            elif isinstance(end_date, date):
                end_date_obj = end_date
            else:
                print(f"[市场数据] 错误: 不支持的 end_date 类型: {type(end_date)}")
                return []
        except ValueError as e:
            print(f"[市场数据] 错误: 无法解析 end_date: {end_date}, 错误: {str(e)}")
            return []
        
        # ========== 路由逻辑 ==========
        # 1. Futures 路由：asset_type == 'futures' 强制使用 AkShare
        if asset_type == "futures" or is_futures_main_code(code):
            print(f"[市场数据] [路由] 期货代码，强制使用 AkShare")
            try:
                df = fetch_futures_data_akshare(code, start_date, end_date)
                if df is None or df.empty:
                    print(f"[市场数据] [路由] AkShare 期货接口未获取到数据")
            except Exception as e:
                print(f"[市场数据] [路由] 获取期货数据时发生异常: {type(e).__name__}: {str(e)}")
                traceback.print_exc()
                df = None
        
        # 2. Stock/ETF 路由：asset_type == 'stock' 使用 yfinance，国内代码强制转换后缀
        elif asset_type == "stock":
            print(f"[市场数据] [路由] 股票/ETF 代码，使用 yfinance（国内代码强制转换后缀）")
            
            # 如果是今天的数据且有数据库会话，先尝试使用回退机制
            if end_date_obj == today and db is not None:
                print(f"[市场数据] [路由] 查询今天的数据，尝试回退机制")
                try:
                    df = fetch_stock_data_with_fallback(code, today, db)
                    if df is not None and not df.empty:
                        print(f"[市场数据] [路由] 回退机制成功获取数据")
                except Exception as e:
                    print(f"[市场数据] [路由] 回退机制执行时发生异常: {type(e).__name__}: {str(e)}")
                    traceback.print_exc()
                    df = None
            
            # 如果回退机制失败或不是今天的数据，使用 yfinance
            if df is None or df.empty:
                try:
                    # 国内代码强制转换后缀（.SS/.SZ），修复 404 无法识别的问题
                    if is_domestic_code(code):
                        # 确保代码格式正确，转换为 yfinance 格式
                        yf_symbol = convert_to_yfinance_symbol(code)
                        print(f"[市场数据] [路由] 国内代码转换: {code} -> {yf_symbol}")
                        df = fetch_stock_data_yfinance(yf_symbol, start_date, end_date, use_realtime=(end_date_obj == today))
                    else:
                        # 非国内代码直接使用 yfinance
                        df = fetch_stock_data_yfinance(code, start_date, end_date, use_realtime=(end_date_obj == today))
                    
                    if df is None or df.empty:
                        print(f"[市场数据] [路由] yfinance 未获取到数据")
                except YFinanceRateLimitError as e:
                    print(f"[市场数据] [路由] yfinance 触发限频，自动降级到 AkShare: {str(e)}")
                    # RateLimitError 且为国内资产，自动尝试 AkShare 备选路径
                    if is_domestic_code(code):
                        try:
                            df = fetch_stock_data_akshare(code, start_date, end_date)
                            if df is not None and not df.empty:
                                print(f"[市场数据] [路由] 降级到 AkShare 成功获取数据")
                        except Exception as ak_e:
                            print(f"[市场数据] [路由] AkShare 备选路径也失败: {type(ak_e).__name__}: {str(ak_e)}")
                    # 如果 AkShare 也失败，尝试从缓存读取
                    if (df is None or df.empty) and db is not None:
                        df = fetch_cached_market_data(code, start_date, end_date, db)
                        if df is not None and not df.empty:
                            print(f"[市场数据] [路由] 从数据库缓存读取数据")
                except Exception as e:
                    print(f"[市场数据] [路由] 获取股票数据时发生异常: {type(e).__name__}: {str(e)}")
                    traceback.print_exc()
                    # 异常情况下，如果是国内代码，尝试 AkShare 备选
                    if is_domestic_code(code):
                        try:
                            df = fetch_stock_data_akshare(code, start_date, end_date)
                        except:
                            pass
                    # 如果仍然失败，尝试从缓存读取
                    if (df is None or df.empty) and db is not None:
                        df = fetch_cached_market_data(code, start_date, end_date, db)
        
        # 3. Fund 路由：asset_type == 'fund' 强制使用 AkShare
        elif asset_type == "fund":
            print(f"[市场数据] [路由] 基金代码，强制使用 AkShare")
            try:
                df = fetch_fund_data(code, start_date, end_date)
                if df is None or df.empty:
                    print(f"[市场数据] [路由] AkShare 基金接口未获取到数据")
            except Exception as e:
                print(f"[市场数据] [路由] 获取基金数据时发生异常: {type(e).__name__}: {str(e)}")
                traceback.print_exc()
                df = None
        else:
            print(f"[市场数据] [路由] 错误: 不支持的资产类型: {asset_type}")
            return []
        
        if df is None or df.empty:
            print(f"[市场数据] ===== 未获取到数据，返回空列表 =====")
            return []
        
        print(f"[市场数据] 开始解析市场数据...")
        try:
            result = parse_market_data(df, asset_type, code)
            print(f"[市场数据] ===== 成功解析 {len(result)} 条数据 =====")
            return result
        except ValueError as e:
            print(f"[市场数据] 错误: 解析市场数据时发生值错误: {str(e)}")
            traceback.print_exc()
            return []
        except Exception as e:
            print(f"[市场数据] 错误: 解析市场数据时发生异常: {type(e).__name__}: {str(e)}")
            traceback.print_exc()
            return []
    except ValueError as e:
        print(f"[市场数据] 错误: 获取资产数据时发生值错误: {str(e)}")
        traceback.print_exc()
        return []
    except Exception as e:
        print(f"[市场数据] 错误: 获取资产数据时发生未预期的异常: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        return []


def store_market_data(
    asset_id: int,
    market_data_list: List[Dict],
    db: Session
) -> int:
    """
    存储市场数据
    
    Returns:
        存储的数据条数
    """
    print(f"[市场数据] 开始存储市场数据: asset_id={asset_id}, 数据条数={len(market_data_list)}")
    
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        print(f"[市场数据] 错误: 资产不存在 (asset_id={asset_id})")
        return 0
    
    stored_count = 0
    updated_count = 0
    baseline_date_obj = date.fromisoformat(BASELINE_DATE)
    
    for idx, data in enumerate(market_data_list, 1):
        try:
            date_obj = date.fromisoformat(data["date"])
            
            # 打印输入数据中的财务指标（用于调试）
            if idx == 1:
                print(f"[市场数据] 输入数据中的财务指标: PE={data.get('pe_ratio')}, PB={data.get('pb_ratio')}, 市值={data.get('market_cap')}, EPS={data.get('eps_forecast')}")
            
            # 检查是否已存在
            existing = db.query(MarketData).filter(
                MarketData.asset_id == asset_id,
                MarketData.date == date_obj
            ).first()
            
            if existing:
                # 更新现有数据 - 显式赋值所有字段，包括财务指标
                existing.close_price = data["close_price"]
                existing.volume = data.get("volume")
                existing.turnover_rate = data.get("turnover_rate")
                
                # 显式赋值财务指标 - 如果数据中有值（包括0），则更新；如果为None，保持原值
                # 使用 "pe_ratio" in data 来检查是否真的提供了这个字段
                # 注意：如果值为 0，可能是真实值，也可能是默认值，我们仍然更新
                if "pe_ratio" in data:
                    val = data["pe_ratio"]
                    # 只有当值不是 None 时才更新（0 是有效值）
                    if val is not None:
                        existing.pe_ratio = val
                if "pb_ratio" in data:
                    val = data["pb_ratio"]
                    if val is not None:
                        existing.pb_ratio = val
                if "market_cap" in data:
                    val = data["market_cap"]
                    # 市值：只有当值大于 0 时才更新（0 可能是计算错误）
                    if val is not None and val > 0:
                        existing.market_cap = val
                if "eps_forecast" in data:
                    val = data["eps_forecast"]
                    if val is not None:
                        existing.eps_forecast = val
                
                # 打印调试信息 - 显示更新前后的值
                print(f"[市场数据] 更新财务指标 (日期={date_obj}): PE={existing.pe_ratio} (输入={data.get('pe_ratio')}), PB={existing.pb_ratio} (输入={data.get('pb_ratio')}), 市值={existing.market_cap} (输入={data.get('market_cap')}), EPS={existing.eps_forecast} (输入={data.get('eps_forecast')})")
                
                if data.get("additional_data"):
                    existing.additional_data = json.dumps(data["additional_data"], ensure_ascii=False)
                updated_count += 1
                if idx % 50 == 0:
                    print(f"[市场数据] 已处理 {idx}/{len(market_data_list)} 条数据 (更新)")
            else:
                # 创建新数据
                # 处理市值：如果为 0，设置为 None（避免存储无效数据）
                market_cap_val = data.get("market_cap")
                if market_cap_val is not None and market_cap_val == 0:
                    market_cap_val = None
                
                market_data = MarketData(
                    asset_id=asset_id,
                    date=date_obj,
                    close_price=data["close_price"],
                    volume=data.get("volume"),
                    turnover_rate=data.get("turnover_rate"),
                    pe_ratio=data.get("pe_ratio"),
                    pb_ratio=data.get("pb_ratio"),
                    market_cap=market_cap_val,
                    eps_forecast=data.get("eps_forecast"),
                    additional_data=json.dumps(data.get("additional_data", {}), ensure_ascii=False) if data.get("additional_data") else None
                )
                db.add(market_data)
                stored_count += 1
                if idx % 50 == 0:
                    print(f"[市场数据] 已处理 {idx}/{len(market_data_list)} 条数据 (新增)")
            
            # 如果是基准日，更新资产的基准价格
            if date_obj == baseline_date_obj and data["close_price"]:
                asset.baseline_price = data["close_price"]
                asset.baseline_date = baseline_date_obj
                print(f"[市场数据] 更新基准价格: {data['close_price']} (日期: {baseline_date_obj})")
            
        except Exception as e:
            print(f"[市场数据] 警告: 存储市场数据失败 (第 {idx} 条): {type(e).__name__}: {str(e)}")
            continue
    
    print(f"[市场数据] 提交数据库事务...")
    db.commit()
    print(f"[市场数据] 存储完成: 新增={stored_count}, 更新={updated_count}, 总计={stored_count + updated_count}")
    return stored_count + updated_count


def custom_update_asset_data(asset_id: int, target_date: str, db: Session) -> Dict:
    """
    单点数据校准：强制覆盖指定日期的数据
    
    核心逻辑：
    1. 忽略现有的"三层过滤"逻辑，直接调用对应的数据源接口
    2. 强制覆盖：使用数据库 upsert 逻辑，如果该记录已存在，则用新抓取的值覆盖旧值
    3. 多源互补：A股/ETF在yfinance失败时自动尝试AkShare
    
    Args:
        asset_id: 资产ID
        target_date: 目标日期 "YYYY-MM-DD"
        db: 数据库会话
    
    Returns:
        {"success": bool, "message": str, "data": dict or None}
    """
    print(f"[市场数据] [单点校准] ========== 开始单点数据校准 ==========")
    print(f"[市场数据] [单点校准] asset_id={asset_id}, target_date={target_date}")
    
    # 验证日期格式
    try:
        target_date = normalize_date_str(target_date)
        target_date_obj = date.fromisoformat(target_date)
    except ValueError as e:
        error_msg = f"日期格式错误: {target_date}, 错误: {str(e)}"
        print(f"[市场数据] [单点校准] ✗ {error_msg}")
        return {"success": False, "message": error_msg, "data": None}
    
    # 获取资产信息
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        error_msg = f"资产不存在 (asset_id={asset_id})"
        print(f"[市场数据] [单点校准] ✗ {error_msg}")
        return {"success": False, "message": error_msg, "data": None}
    
    print(f"[市场数据] [单点校准] 资产信息: ID={asset.id}, 名称={asset.name}, 代码={asset.code}, 类型={asset.asset_type}")
    
    # 计算日期范围：end_date 必须是 target_date 的次日（yfinance 要求）
    end_date_obj = target_date_obj + timedelta(days=1)
    end_date = end_date_obj.strftime('%Y-%m-%d')
    print(f"[市场数据] [单点校准] 日期范围: {target_date} 至 {end_date} (end_date为次日)")
    
    # 强制调用数据源接口（忽略所有过滤逻辑）
    print(f"[市场数据] [单点校准] 强制调用数据源接口获取 {target_date} 的数据...")
    data = None
    data_list = []
    
    try:
        # 1. 期货：直接使用 AkShare
        if asset.asset_type == "futures" or is_futures_main_code(asset.code):
            print(f"[市场数据] [单点校准] 期货代码，使用 AkShare")
            df = fetch_futures_data_akshare(asset.code, target_date, end_date)
            if df is not None and not df.empty:
                # 解析为数据列表
                data_list = parse_market_data(df, asset.asset_type, asset.code)
        
        # 2. 股票/ETF：优先使用 yfinance，失败时尝试 AkShare（仅限A股）
        elif asset.asset_type == "stock":
            print(f"[市场数据] [单点校准] 股票/ETF代码，优先使用 yfinance")
            
            # 首先尝试 yfinance
            try:
                # 判断是否为A股：检查代码格式或 normalize 后的代码是否以6/0/3开头
                normalized_code = normalize_stock_code(asset.code)
                is_ashare = (
                    is_a_share_code(asset.code) or 
                    asset.code.upper().startswith(('SH', 'SZ')) or
                    normalized_code.startswith(('6', '0', '3'))
                )
                if is_ashare:
                    # 转换为 yfinance 格式
                    yf_code = convert_to_yfinance_symbol(asset.code)
                    print(f"[市场数据] [单点校准] A股代码，转换后: {asset.code} -> {yf_code}")
                else:
                    yf_code = asset.code
                    print(f"[市场数据] [单点校准] 非A股代码，使用原始代码: {yf_code}")
                
                df = fetch_stock_data_yfinance(yf_code, target_date, end_date, use_realtime=False)
                if df is not None and not df.empty:
                    print(f"[市场数据] [单点校准] yfinance 成功获取数据")
                    data_list = parse_market_data(df, asset.asset_type, asset.code)
                else:
                    print(f"[市场数据] [单点校准] yfinance 未获取到数据")
            except Exception as e:
                print(f"[市场数据] [单点校准] yfinance 获取失败: {type(e).__name__}: {str(e)}")
            
            # 如果 yfinance 失败且是 A 股，尝试 AkShare（多源互补）
            if (not data_list or len(data_list) == 0) and is_ashare:
                print(f"[市场数据] [单点校准] yfinance 失败，尝试使用 AkShare 进行二次校准...")
                try:
                    # 注意：fetch_stock_data_akshare 内部会调用 normalize_stock_code
                    # 所以这里直接传入原始代码即可
                    df = fetch_stock_data_akshare(asset.code, target_date, end_date)
                    if df is not None and not df.empty:
                        print(f"[市场数据] [单点校准] AkShare 成功获取数据")
                        data_list = parse_market_data(df, asset.asset_type, asset.code)
                    else:
                        print(f"[市场数据] [单点校准] AkShare 也未获取到数据")
                except Exception as e:
                    print(f"[市场数据] [单点校准] AkShare 获取失败: {type(e).__name__}: {str(e)}")
                    traceback.print_exc()
        
        # 3. 基金：强制使用 AkShare（日期补丁：end_date 自动设为 target_date 的后一天）
        elif asset.asset_type == "fund":
            print(f"[市场数据] [单点校准] 基金代码，强制使用 AkShare")
            # 日期补丁：确保 end_date 为 target_date 的后一天，防止区间重叠导致数据为空
            end_date_patched = (target_date_obj + timedelta(days=1)).strftime('%Y-%m-%d')
            print(f"[市场数据] [单点校准] 基金日期补丁: end_date={end_date} -> {end_date_patched}")
            try:
                df = fetch_fund_data(asset.code, target_date, end_date_patched)
                if df is not None and not df.empty:
                    data_list = parse_market_data(df, asset.asset_type, asset.code)
                else:
                    print(f"[市场数据] [单点校准] AkShare 基金接口未获取到数据")
            except Exception as e:
                print(f"[市场数据] [单点校准] 基金数据获取失败: {type(e).__name__}: {str(e)}")
                traceback.print_exc()
        
        # 检查是否获取到数据
        if not data_list or len(data_list) == 0:
            error_msg = f"未能从任何数据源获取到 {target_date} 的数据（yfinance 和 AkShare 均失败）"
            print(f"[市场数据] [单点校准] ✗ {error_msg}")
            return {"success": False, "message": error_msg, "data": None}
        
        # 从数据列表中找到目标日期的数据
        data = None
        for item in data_list:
            if item.get("date") == target_date:
                data = item
                break
        
        # 如果没找到精确匹配，取第一条（可能是日期格式问题）
        if not data and len(data_list) > 0:
            data = data_list[0]
            print(f"[市场数据] [单点校准] 警告: 未找到精确日期匹配，使用第一条数据: {data.get('date')}")
        
        if not data:
            error_msg = f"未能从数据源获取到 {target_date} 的数据"
            print(f"[市场数据] [单点校准] ✗ {error_msg}")
            return {"success": False, "message": error_msg, "data": None}
        
        print(f"[市场数据] [单点校准] 成功获取数据: {data}")
        
        # 强制覆盖数据库记录（upsert）
        date_obj = date.fromisoformat(data["date"])
        existing = db.query(MarketData).filter(
            MarketData.asset_id == asset_id,
            MarketData.date == date_obj
        ).first()
        
        if existing:
            # 强制覆盖所有字段
            print(f"[市场数据] [单点校准] 记录已存在，强制覆盖所有字段...")
            existing.close_price = data["close_price"]
            existing.volume = data.get("volume")
            existing.turnover_rate = data.get("turnover_rate")
            
            # 强制覆盖财务指标（即使为 None 也覆盖）
            existing.pe_ratio = data.get("pe_ratio")
            existing.pb_ratio = data.get("pb_ratio")
            existing.market_cap = data.get("market_cap") if data.get("market_cap") and data.get("market_cap") > 0 else None
            existing.eps_forecast = data.get("eps_forecast")
            
            if data.get("additional_data"):
                existing.additional_data = json.dumps(data["additional_data"], ensure_ascii=False)
            else:
                existing.additional_data = None
            
            db.commit()
            print(f"[市场数据] [单点校准] ✓ 成功覆盖记录 (日期: {date_obj})")
            return {
                "success": True,
                "message": f"成功覆盖 {target_date} 的数据",
                "data": {
                    "date": target_date,
                    "close_price": existing.close_price,
                    "volume": existing.volume,
                    "turnover_rate": existing.turnover_rate,
                    "pe_ratio": existing.pe_ratio,
                    "pb_ratio": existing.pb_ratio,
                    "market_cap": existing.market_cap,
                    "eps_forecast": existing.eps_forecast,
                }
            }
        else:
            # 创建新记录
            print(f"[市场数据] [单点校准] 记录不存在，创建新记录...")
            market_cap_val = data.get("market_cap")
            if market_cap_val is not None and market_cap_val == 0:
                market_cap_val = None
            
            market_data = MarketData(
                asset_id=asset_id,
                date=date_obj,
                close_price=data["close_price"],
                volume=data.get("volume"),
                turnover_rate=data.get("turnover_rate"),
                pe_ratio=data.get("pe_ratio"),
                pb_ratio=data.get("pb_ratio"),
                market_cap=market_cap_val,
                eps_forecast=data.get("eps_forecast"),
                additional_data=json.dumps(data.get("additional_data", {}), ensure_ascii=False) if data.get("additional_data") else None
            )
            db.add(market_data)
            db.commit()
            print(f"[市场数据] [单点校准] ✓ 成功创建新记录 (日期: {date_obj})")
            return {
                "success": True,
                "message": f"成功创建 {target_date} 的数据",
                "data": {
                    "date": target_date,
                    "close_price": market_data.close_price,
                    "volume": market_data.volume,
                    "turnover_rate": market_data.turnover_rate,
                    "pe_ratio": market_data.pe_ratio,
                    "pb_ratio": market_data.pb_ratio,
                    "market_cap": market_data.market_cap,
                    "eps_forecast": market_data.eps_forecast,
                }
            }
            
    except Exception as e:
        error_msg = f"单点数据校准失败: {type(e).__name__}: {str(e)}"
        print(f"[市场数据] [单点校准] ✗ {error_msg}")
        traceback.print_exc()
        db.rollback()
        return {"success": False, "message": error_msg, "data": None}


def update_asset_data(asset_id: int, db: Session, force: bool = False) -> Dict:
    """
    更新资产数据 - 区分"今日"强制刷新和"历史"按需补全
    
    "今日"逻辑：
    - 获取当前自然日（北京时间）
    - 对于数据库中日期等于"今日"的记录，每次点击更新都强制发起 API 请求
    - 如果今日 API 返回空（未开盘或接口延迟），则继续执行回溯逻辑，取上一个交易日的价格作为临时值，并在日志中标记为临时数据
    
    "历史"逻辑：
    - 对于日期早于"今日"的所有记录：
    - 优先查库：如果 close_price 且 pe_ratio 等核心指标均不为空，则直接跳过
    - 按需补全：只有当数据库中该历史记录缺失或指标全为 null 时，才发起 API 请求获取
    
    Args:
        asset_id: 资产ID
        db: 数据库会话
        force: 是否强制更新（即使已有数据）- 此参数保留但不再使用，因为"今日"逻辑已强制刷新
    
    Returns:
        {"success": bool, "message": str, "stored_count": int, "new_data_count": int, "filled_metrics_count": int, "today_updated": bool}
    """
    print(f"[市场数据] ========== 开始更新资产数据 (asset_id={asset_id}, force={force}) ==========")
    
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        print(f"[市场数据] 错误: 资产不存在 (asset_id={asset_id})")
        return {"success": False, "message": "资产不存在", "stored_count": 0, "new_data_count": 0, "filled_metrics_count": 0, "today_updated": False}
    
    print(f"[市场数据] 资产信息: ID={asset.id}, 名称={asset.name}, 代码={asset.code}, 类型={asset.asset_type}")
    
    # 获取当前自然日（北京时间）
    beijing_time = get_beijing_time()
    today = beijing_time.date()
    
    # 确定扫描日期范围：从基准日期到今天
    baseline_date_obj = date.fromisoformat(BASELINE_DATE) if isinstance(BASELINE_DATE, str) else BASELINE_DATE
    
    print(f"[市场数据] 扫描日期范围: {baseline_date_obj} 至 {today} (今日: {today})")
    
    # 统计变量
    new_data_count = 0  # 新增的数据记录数
    filled_metrics_count = 0  # 补全财务指标的记录数
    skipped_count = 0  # 跳过的完整记录数
    today_updated = False  # 今日是否更新成功
    today_is_temporary = False  # 今日数据是否为临时数据
    
    # 获取最新的财务指标（作为基准用于反推历史数据）
    latest_with_metrics = db.query(MarketData).filter(
        MarketData.asset_id == asset_id,
        MarketData.pe_ratio.isnot(None),
        MarketData.pe_ratio != 0
    ).order_by(MarketData.date.desc()).first()
    
    if not latest_with_metrics:
        latest_with_metrics = db.query(MarketData).filter(
            MarketData.asset_id == asset_id
        ).order_by(MarketData.date.desc()).first()
    
    # 获取基准财务指标（用于反推历史数据）
    ref_pe = None
    ref_pb = None
    ref_market_cap = None
    ref_eps = None
    ref_price = None
    ref_date = None
    
    if latest_with_metrics:
        ref_pe = latest_with_metrics.pe_ratio if latest_with_metrics.pe_ratio and latest_with_metrics.pe_ratio != 0 else None
        ref_pb = latest_with_metrics.pb_ratio if latest_with_metrics.pb_ratio and latest_with_metrics.pb_ratio != 0 else None
        ref_market_cap = latest_with_metrics.market_cap if latest_with_metrics.market_cap and latest_with_metrics.market_cap > 0 else None
        ref_eps = latest_with_metrics.eps_forecast if latest_with_metrics.eps_forecast else None
        ref_price = latest_with_metrics.close_price
        ref_date = latest_with_metrics.date
        
        print(f"[市场数据] 基准财务指标 (日期: {ref_date}): PE={ref_pe}, PB={ref_pb}, 市值={ref_market_cap}, EPS={ref_eps}, 价格={ref_price}")
    
    # ========== 第一步：处理"今日"数据（强制刷新 - 15:30分界） ==========
    print(f"[市场数据] ========== 【今日实时覆盖】开始处理今日数据 ({today}) ==========")
    
    # 判断是否在交易时间内（15:30之前为实时，之后为收盘价）
    in_trading_hours = is_trading_hours()
    beijing_time = get_beijing_time()
    current_time_str = beijing_time.strftime("%H:%M")
    
    if in_trading_hours:
        print(f"[市场数据] [今日实时覆盖] 当前时间 {current_time_str} 在交易时间内（15:30之前），更新实时价格和成交额")
    else:
        print(f"[市场数据] [今日实时覆盖] 当前时间 {current_time_str} 已收盘（15:30之后），视为收盘价并存库")
    
    try:
        # 今日数据必须发起 API 请求
        print(f"[市场数据] [今日实时覆盖] 强制发起 API 请求获取今日数据...")
        today_data_list = fetch_asset_data(
            code=asset.code,
            asset_type=asset.asset_type,
            start_date=today.isoformat(),
            end_date=today.isoformat(),
            db=db
        )
        
        if today_data_list and len(today_data_list) > 0:
            today_data = today_data_list[0]
            today_price = today_data.get("close_price")
            today_pe = today_data.get("pe_ratio")
            today_pb = today_data.get("pb_ratio")
            today_market_cap = today_data.get("market_cap")
            today_eps = today_data.get("eps_forecast")
            
            if today_price:
                # API 返回了今日数据，检查数据库中是否已有今日记录
                existing_today = db.query(MarketData).filter(
                    MarketData.asset_id == asset_id,
                    MarketData.date == today
                ).first()
                
                if existing_today:
                    # 更新现有记录（覆盖早盘的临时数据）
                    print(f"[市场数据] [今日实时覆盖] 更新今日记录: 价格={today_price}, PE={today_pe}, PB={today_pb}, 市值={today_market_cap}")
                    existing_today.close_price = today_price
                    existing_today.volume = today_data.get("volume")
                    existing_today.turnover_rate = today_data.get("turnover_rate")
                    
                    # 更新财务指标（如果 API 返回了值）
                    if today_pe is not None:
                        existing_today.pe_ratio = today_pe
                    if today_pb is not None:
                        existing_today.pb_ratio = today_pb
                    if today_market_cap is not None and today_market_cap > 0:
                        existing_today.market_cap = today_market_cap
                    if today_eps is not None:
                        existing_today.eps_forecast = today_eps
                    
                    if today_data.get("additional_data"):
                        existing_today.additional_data = json.dumps(today_data.get("additional_data", {}), ensure_ascii=False)
                    
                    today_updated = True
                    print(f"[市场数据] [今日实时覆盖] ✓ 成功覆盖今日数据: 价格={today_price}, PE={existing_today.pe_ratio}, PB={existing_today.pb_ratio}, 市值={existing_today.market_cap}")
                else:
                    # 创建新记录
                    print(f"[市场数据] [今日实时覆盖] 创建今日新记录: 价格={today_price}, PE={today_pe}, PB={today_pb}, 市值={today_market_cap}")
                    market_data = MarketData(
                        asset_id=asset_id,
                        date=today,
                        close_price=today_price,
                        volume=today_data.get("volume"),
                        turnover_rate=today_data.get("turnover_rate"),
                        pe_ratio=today_pe,
                        pb_ratio=today_pb,
                        market_cap=today_market_cap if today_market_cap and today_market_cap > 0 else None,
                        eps_forecast=today_eps,
                        additional_data=json.dumps(today_data.get("additional_data", {}), ensure_ascii=False) if today_data.get("additional_data") else None
                    )
                    db.add(market_data)
                    new_data_count += 1
                    today_updated = True
                    print(f"[市场数据] [今日实时覆盖] ✓ 成功创建今日数据")
            else:
                print(f"[市场数据] [今日实时覆盖] 警告: API 返回了数据但价格为空")
        else:
            # API 返回空（未开盘或接口延迟），执行回溯逻辑
            print(f"[市场数据] [今日实时覆盖] API 返回空，执行回溯逻辑获取临时数据...")
            
            # 从数据库中查找最近一个交易日的数据
            latest_data = db.query(MarketData).filter(
                MarketData.asset_id == asset_id,
                MarketData.date < today
            ).order_by(MarketData.date.desc()).first()
            
            if latest_data:
                # 使用最近交易日的数据作为临时值
                print(f"[市场数据] [今日实时覆盖] 使用最近交易日 {latest_data.date} 的数据作为临时值 (is_temporary=True)")
                
                existing_today = db.query(MarketData).filter(
                    MarketData.asset_id == asset_id,
                    MarketData.date == today
                ).first()
                
                if existing_today:
                    # 更新现有记录为临时数据
                    existing_today.close_price = latest_data.close_price
                    existing_today.volume = latest_data.volume
                    existing_today.turnover_rate = latest_data.turnover_rate
                    existing_today.pe_ratio = latest_data.pe_ratio
                    existing_today.pb_ratio = latest_data.pb_ratio
                    existing_today.market_cap = latest_data.market_cap
                    existing_today.eps_forecast = latest_data.eps_forecast
                    print(f"[市场数据] [今日实时覆盖] 更新今日记录为临时数据 (is_temporary=True): 价格={latest_data.close_price}")
                else:
                    # 创建临时记录
                    market_data = MarketData(
                        asset_id=asset_id,
                        date=today,
                        close_price=latest_data.close_price,
                        volume=latest_data.volume,
                        turnover_rate=latest_data.turnover_rate,
                        pe_ratio=latest_data.pe_ratio,
                        pb_ratio=latest_data.pb_ratio,
                        market_cap=latest_data.market_cap,
                        eps_forecast=latest_data.eps_forecast,
                        additional_data=latest_data.additional_data
                    )
                    db.add(market_data)
                    new_data_count += 1
                    print(f"[市场数据] [今日实时覆盖] 创建今日临时记录 (is_temporary=True): 价格={latest_data.close_price}")
                
                today_is_temporary = True
                today_updated = True
            else:
                print(f"[市场数据] [今日实时覆盖] 警告: 数据库中无历史数据可回溯")
    except Exception as e:
        print(f"[市场数据] [今日实时覆盖] 处理今日数据时发生异常: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
    
    # 更新基准财务指标（如果今日数据获取成功）
    if today_updated and not today_is_temporary:
        try:
            today_record = db.query(MarketData).filter(
                MarketData.asset_id == asset_id,
                MarketData.date == today
            ).first()
            if today_record and today_record.pe_ratio and today_record.pe_ratio != 0:
                ref_pe = today_record.pe_ratio
                ref_pb = today_record.pb_ratio if today_record.pb_ratio else None
                ref_market_cap = today_record.market_cap if today_record.market_cap and today_record.market_cap > 0 else None
                ref_eps = today_record.eps_forecast if today_record.eps_forecast else None
                ref_price = today_record.close_price
                ref_date = today_record.date
                print(f"[市场数据] [今日实时覆盖] 更新基准财务指标: PE={ref_pe}, PB={ref_pb}, 市值={ref_market_cap}")
        except Exception as e:
            print(f"[市场数据] [今日实时覆盖] 更新基准财务指标时发生异常: {str(e)}")
    
    # ========== 第二步：处理"历史"数据（按需补全 - 三层过滤策略） ==========
    print(f"[市场数据] ========== 【历史缺失补全】开始处理历史数据（三层过滤策略） ==========")
    
    # 第一层：查找缺失的历史日期（仅查找最近5天的缺失日期，防止无限回溯）
    missing_dates = []
    MAX_BACKTRACK_DAYS = 5  # 最多回溯5天
    
    # 从今天往前找缺失的日期
    check_date = today - timedelta(days=1)
    days_checked = 0
    
    while check_date >= baseline_date_obj and days_checked < MAX_BACKTRACK_DAYS:
        # 第二层：日历过滤 - 非交易日跳过，直接读库
        if not is_trading_day(check_date):
            print(f"[市场数据] [三层过滤] 日期 {check_date} 是非交易日，跳过 API 请求，直接读库")
            check_date -= timedelta(days=1)
            continue
        
        days_checked += 1
        
        # 检查该日期是否已存在且数据完整
        existing_record = db.query(MarketData).filter(
            MarketData.asset_id == asset_id,
            MarketData.date == check_date
        ).first()
        
        if existing_record:
            # 检查数据是否完整（包括价格、市盈率、市净率）
            has_price = existing_record.close_price is not None
            has_pe = existing_record.pe_ratio is not None and existing_record.pe_ratio != 0
            has_pb = existing_record.pb_ratio is not None and existing_record.pb_ratio != 0
            has_metrics = has_pe or has_pb or (existing_record.market_cap is not None and existing_record.market_cap > 0)
            
            # 如果价格和财务指标都完整，跳过
            if has_price and has_metrics and has_pe and has_pb:
                # 数据完整（包括 PE 和 PB），跳过
                skipped_count += 1
            else:
                # 数据不完整（缺少价格或缺少 PE/PB），需要补全
                missing_dates.append(check_date)
        else:
            # 记录不存在，需要获取
            missing_dates.append(check_date)
        
        check_date -= timedelta(days=1)
    
    print(f"[市场数据] [三层过滤] 找到 {len(missing_dates)} 个缺失日期（最多回溯 {MAX_BACKTRACK_DAYS} 天）")
    
    # 遍历缺失的日期，发起 API 请求补全
    for current_date in missing_dates:
        
        try:
            # 第三层：日历过滤 - 确保是交易日才发起 API 请求
            if should_skip_api_request(current_date, db, asset_id):
                # 非交易日，跳过 API 请求，直接读库
                skipped_count += 1
                continue
            
            # 检查该日期是否已存在记录
            existing_record = db.query(MarketData).filter(
                MarketData.asset_id == asset_id,
                MarketData.date == current_date
            ).first()
            
            if existing_record:
                # 检查数据是否完整（核心指标：close_price、pe_ratio、pb_ratio）
                has_price = existing_record.close_price is not None
                has_pe = existing_record.pe_ratio is not None and existing_record.pe_ratio != 0
                has_pb = existing_record.pb_ratio is not None and existing_record.pb_ratio != 0
                has_metrics = has_pe or has_pb or (existing_record.market_cap is not None and existing_record.market_cap > 0)
                
                if has_price and has_pe and has_pb:
                    # 数据完整（包括价格、PE、PB），跳过（优先查库）
                    skipped_count += 1
                    if skipped_count % 50 == 0:
                        print(f"[市场数据] [历史缺失补全] 已跳过 {skipped_count} 条完整记录...")
                elif has_price and (not has_pe or not has_pb):
                    # 有价格但缺少 PE 或 PB，需要发起 API 请求补全（遵循 5 天限制）
                    print(f"[市场数据] [历史缺失补全] 日期 {current_date} 缺少 PE/PB 指标，发起 API 请求补全...")
                    try:
                        hist_data_list = fetch_asset_data(
                            code=asset.code,
                            asset_type=asset.asset_type,
                            start_date=current_date.isoformat(),
                            end_date=current_date.isoformat(),
                            db=db
                        )
                        
                        if hist_data_list and len(hist_data_list) > 0:
                            hist_data = hist_data_list[0]
                            
                            # 如果 API 返回了财务指标，使用 API 的值；否则反推
                            if hist_data.get("pe_ratio") is not None:
                                existing_record.pe_ratio = hist_data.get("pe_ratio")
                            elif not has_pe and ref_pe and ref_price and ref_price > 0:
                                hist_price = existing_record.close_price
                                price_ratio = hist_price / ref_price
                                existing_record.pe_ratio = ref_pe * price_ratio
                            
                            if hist_data.get("pb_ratio") is not None:
                                existing_record.pb_ratio = hist_data.get("pb_ratio")
                            elif not has_pb and ref_pb and ref_price and ref_price > 0:
                                hist_price = existing_record.close_price
                                price_ratio = hist_price / ref_price
                                existing_record.pb_ratio = ref_pb * price_ratio
                            
                            # 更新其他字段（如果 API 返回了）
                            if hist_data.get("close_price") is not None:
                                existing_record.close_price = hist_data.get("close_price")
                            if hist_data.get("volume") is not None:
                                existing_record.volume = hist_data.get("volume")
                            if hist_data.get("turnover_rate") is not None:
                                existing_record.turnover_rate = hist_data.get("turnover_rate")
                            
                            if hist_data.get("market_cap") is not None and hist_data.get("market_cap") > 0:
                                existing_record.market_cap = hist_data.get("market_cap")
                            elif ref_market_cap and ref_price and ref_price > 0:
                                hist_price = existing_record.close_price
                                price_ratio = hist_price / ref_price
                                existing_record.market_cap = ref_market_cap * price_ratio
                            
                            if hist_data.get("eps_forecast") is not None:
                                existing_record.eps_forecast = hist_data.get("eps_forecast")
                            elif ref_eps:
                                existing_record.eps_forecast = ref_eps
                            
                            if hist_data.get("additional_data"):
                                existing_record.additional_data = json.dumps(hist_data.get("additional_data", {}), ensure_ascii=False)
                            
                            filled_metrics_count += 1
                            pe_str = f"{existing_record.pe_ratio:.2f}" if existing_record.pe_ratio is not None else "N/A"
                            pb_str = f"{existing_record.pb_ratio:.2f}" if existing_record.pb_ratio is not None else "N/A"
                            print(f"[市场数据] [历史缺失补全] 补全 PE/PB 指标 (日期: {current_date}): PE={pe_str}, PB={pb_str}")
                    except Exception as e:
                        print(f"[市场数据] [历史缺失补全] 获取日期 {current_date} 的 PE/PB 数据失败: {type(e).__name__}: {str(e)}")
                else:
                    # 价格也为空，需要获取数据
                    print(f"[市场数据] [历史缺失补全] 日期 {current_date} 数据不完整（缺少价格），发起 API 请求...")
                    try:
                        hist_data_list = fetch_asset_data(
                            code=asset.code,
                            asset_type=asset.asset_type,
                            start_date=current_date.isoformat(),
                            end_date=current_date.isoformat(),
                            db=db
                        )
                        
                        if hist_data_list and len(hist_data_list) > 0:
                            hist_data = hist_data_list[0]
                            hist_price = hist_data.get("close_price")
                            
                            if hist_price:
                                # 更新现有记录
                                existing_record.close_price = hist_price
                                existing_record.volume = hist_data.get("volume")
                                existing_record.turnover_rate = hist_data.get("turnover_rate")
                                
                                # 如果 API 返回了财务指标，使用 API 的值；否则反推
                                if hist_data.get("pe_ratio") is not None:
                                    existing_record.pe_ratio = hist_data.get("pe_ratio")
                                elif ref_pe and ref_price and ref_price > 0:
                                    price_ratio = hist_price / ref_price
                                    existing_record.pe_ratio = ref_pe * price_ratio
                                
                                if hist_data.get("pb_ratio") is not None:
                                    existing_record.pb_ratio = hist_data.get("pb_ratio")
                                elif ref_pb and ref_price and ref_price > 0:
                                    price_ratio = hist_price / ref_price
                                    existing_record.pb_ratio = ref_pb * price_ratio
                                
                                if hist_data.get("market_cap") is not None and hist_data.get("market_cap") > 0:
                                    existing_record.market_cap = hist_data.get("market_cap")
                                elif ref_market_cap and ref_price and ref_price > 0:
                                    price_ratio = hist_price / ref_price
                                    existing_record.market_cap = ref_market_cap * price_ratio
                                
                                if hist_data.get("eps_forecast") is not None:
                                    existing_record.eps_forecast = hist_data.get("eps_forecast")
                                elif ref_eps:
                                    existing_record.eps_forecast = ref_eps
                                
                                if hist_data.get("additional_data"):
                                    existing_record.additional_data = json.dumps(hist_data.get("additional_data", {}), ensure_ascii=False)
                                
                                filled_metrics_count += 1
                                pe_str = f"{existing_record.pe_ratio:.2f}" if existing_record.pe_ratio is not None else "N/A"
                                pb_str = f"{existing_record.pb_ratio:.2f}" if existing_record.pb_ratio is not None else "N/A"
                                print(f"[市场数据] [历史缺失补全] 更新记录 (日期: {current_date}): 价格={hist_price}, PE={pe_str}, PB={pb_str}")
                    except Exception as e:
                        print(f"[市场数据] [历史缺失补全] 获取日期 {current_date} 数据失败: {type(e).__name__}: {str(e)}")
            else:
                # 记录不存在，需要获取历史价格并补全财务指标（按需补全）
                print(f"[市场数据] [历史缺失补全] 日期 {current_date} 记录不存在，发起 API 请求...")
                try:
                    hist_data_list = fetch_asset_data(
                        code=asset.code,
                        asset_type=asset.asset_type,
                        start_date=current_date.isoformat(),
                        end_date=current_date.isoformat(),
                        db=db
                    )
                    
                    if hist_data_list and len(hist_data_list) > 0:
                        hist_data = hist_data_list[0]
                        hist_price = hist_data.get("close_price")
                        
                        if hist_price:
                            # 创建新记录
                            market_data = MarketData(
                                asset_id=asset_id,
                                date=current_date,
                                close_price=hist_price,
                                volume=hist_data.get("volume"),
                                turnover_rate=hist_data.get("turnover_rate"),
                                pe_ratio=None,
                                pb_ratio=None,
                                market_cap=None,
                                eps_forecast=None,
                                additional_data=json.dumps(hist_data.get("additional_data", {}), ensure_ascii=False) if hist_data.get("additional_data") else None
                            )
                            
                            # 如果 API 返回了财务指标，使用 API 的值；否则反推
                            if hist_data.get("pe_ratio") is not None:
                                market_data.pe_ratio = hist_data.get("pe_ratio")
                            elif ref_pe and ref_price and ref_price > 0:
                                price_ratio = hist_price / ref_price
                                market_data.pe_ratio = ref_pe * price_ratio
                            
                            if hist_data.get("pb_ratio") is not None:
                                market_data.pb_ratio = hist_data.get("pb_ratio")
                            elif ref_pb and ref_price and ref_price > 0:
                                price_ratio = hist_price / ref_price
                                market_data.pb_ratio = ref_pb * price_ratio
                            
                            if hist_data.get("market_cap") is not None and hist_data.get("market_cap") > 0:
                                market_data.market_cap = hist_data.get("market_cap")
                            elif ref_market_cap and ref_price and ref_price > 0:
                                price_ratio = hist_price / ref_price
                                market_data.market_cap = ref_market_cap * price_ratio
                            
                            if hist_data.get("eps_forecast") is not None:
                                market_data.eps_forecast = hist_data.get("eps_forecast")
                            elif ref_eps:
                                market_data.eps_forecast = ref_eps
                            
                            pe_str = f"{market_data.pe_ratio:.2f}" if market_data.pe_ratio is not None else "N/A"
                            print(f"[市场数据] [历史缺失补全] 新增记录 (日期: {current_date}): 价格={hist_price}, PE={pe_str}")
                            
                            db.add(market_data)
                            new_data_count += 1
                except Exception as e:
                    # 静默处理异常，只记录日志
                    print(f"[市场数据] [历史缺失补全] 获取日期 {current_date} 数据失败: {type(e).__name__}")
        except Exception as e:
            # 单个日期处理失败不应该导致整个资产更新失败
            print(f"[市场数据] [历史缺失补全] 警告: 处理日期 {current_date} 时发生异常: {type(e).__name__}: {str(e)}")
            traceback.print_exc()
    
    # 提交所有更改
    try:
        db.commit()
        total_count = new_data_count + filled_metrics_count
        
        # 构建返回消息
        message_parts = []
        if today_updated:
            if today_is_temporary:
                message_parts.append(f"今日数据已更新（临时数据，等待真实价格）")
            else:
                message_parts.append(f"今日数据已实时覆盖")
        if new_data_count > 0:
            message_parts.append(f"新增 {new_data_count} 条历史数据")
        if filled_metrics_count > 0:
            message_parts.append(f"补全 {filled_metrics_count} 条历史缺失指标")
        if skipped_count > 0 and not message_parts:
            message_parts.append(f"数据已完整，无需更新（跳过了 {skipped_count} 条完整记录）")
        
        message = "；".join(message_parts) if message_parts else "无数据更新"
        
        print(f"[市场数据] ========== 资产数据更新完成 (asset_id={asset_id}) ==========")
        print(f"[市场数据] 统计: 今日更新={'是' if today_updated else '否'}, 今日临时={'是' if today_is_temporary else '否'}, 新增={new_data_count}, 补全指标={filled_metrics_count}, 跳过={skipped_count}, 总计={total_count}")
        
        return {
            "success": True,
            "message": message,
            "stored_count": total_count,
            "new_data_count": new_data_count,
            "filled_metrics_count": filled_metrics_count,
            "today_updated": today_updated,
            "today_is_temporary": today_is_temporary
        }
    except Exception as e:
        print(f"[市场数据] 错误: 提交数据时发生异常: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        db.rollback()
        return {
            "success": False,
            "message": f"更新失败: {str(e)}",
            "stored_count": 0,
            "new_data_count": 0,
            "filled_metrics_count": 0,
            "today_updated": False,
            "today_is_temporary": False
        }


def update_all_assets_data(db: Session, force: bool = False) -> Dict:
    """更新所有资产数据"""
    print(f"[市场数据] ========== 开始批量更新所有资产数据 (force={force}) ==========")
    
    assets = db.query(Asset).all()
    print(f"[市场数据] 找到 {len(assets)} 个资产需要更新")
    
    results = {
        "total": len(assets),
        "success": 0,
        "failed": 0,
        "details": []
    }
    
    for idx, asset in enumerate(assets, 1):
        print(f"[市场数据] -------- 处理资产 {idx}/{len(assets)}: {asset.name} (ID: {asset.id}) --------")
        
        # 在资产之间添加随机延迟（1-3秒），降低被封 IP 的风险
        if idx > 1:  # 第一个资产不需要延迟
            delay = random.uniform(1, 3)
            print(f"[市场数据] 随机延迟 {delay:.2f} 秒，降低 IP 频率限制风险...")
            time.sleep(delay)
        
        try:
            result = update_asset_data(asset.id, db, force)
            if result["success"]:
                results["success"] += 1
                print(f"[市场数据] ✓ 资产 {asset.name} 更新成功")
            else:
                results["failed"] += 1
                print(f"[市场数据] ✗ 资产 {asset.name} 更新失败: {result.get('message', '未知错误')}")
            results["details"].append({
                "asset_id": asset.id,
                "asset_name": asset.name,
                "result": result
            })
        except Exception as e:
            # 单个资产失败不应该导致整个批量更新崩溃
            results["failed"] += 1
            error_msg = f"处理资产时发生异常: {type(e).__name__}: {str(e)}"
            print(f"[市场数据] ✗ 资产 {asset.name} 处理异常: {error_msg}")
            traceback.print_exc()
            results["details"].append({
                "asset_id": asset.id,
                "asset_name": asset.name,
                "result": {
                    "success": False,
                    "message": error_msg,
                    "stored_count": 0,
                    "new_data_count": 0,
                    "filled_metrics_count": 0
                }
            })
    
    print(f"[市场数据] ========== 批量更新完成: 总计={results['total']}, 成功={results['success']}, 失败={results['failed']} ==========")
    return results


def calculate_stability_metrics(asset_id: int, db: Session) -> Dict:
    """
    计算资产稳健度指标（增强鲁棒性版本）
    
    阈值校验：
    - 数据量 N < 2：返回年化波动率=0.0, 稳健性评分=0.0，备注记录"数据样本不足，待积累"
    - 数据量 N >= 2：正常计算
    
    Args:
        asset_id: 资产ID
        db: 数据库会话
    
    Returns:
        dict: {
            "stability_score": float,  # 稳健性评分 (0-100)
            "annual_volatility": float,  # 年化波动率 (%)
            "daily_returns": List[float],  # 最近20个交易日的每日收益率 (%)
            "remark": str  # 备注信息（可选）
        }
    """
    print(f"[市场数据] [稳健度计算] 开始计算资产 {asset_id} 的稳健度指标")
    
    try:
        # 获取从基准日期（2026-01-05）到今天的所有市场数据
        baseline_date_obj = date.fromisoformat(BASELINE_DATE) if isinstance(BASELINE_DATE, str) else BASELINE_DATE
        today = get_beijing_time().date()
        
        print(f"[市场数据] [稳健度计算] 查询日期范围: {baseline_date_obj} 至 {today}")
        
        # 查询市场数据，按日期升序排列
        # 使用 yield_per 优化大数据量查询，但这里数据量通常不大，直接使用 all() 即可
        market_data_list = db.query(MarketData).filter(
            MarketData.asset_id == asset_id,
            MarketData.date >= baseline_date_obj,
            MarketData.date <= today
        ).order_by(MarketData.date.asc()).all()
        
        # 阈值校验：数据量检查（需要至少3条数据才能产生2个收益率样本）
        data_count = len(market_data_list) if market_data_list else 0
        
        if data_count < 3:
            print(f"[市场数据] [稳健度计算] 数据积累中 (N={data_count} < 3)，返回默认值")
            return {
                "stability_score": 0.0,
                "annual_volatility": 0.0,
                "daily_returns": [],
                "remark": "数据积累中"
            }
        
        print(f"[市场数据] [稳健度计算] 找到 {data_count} 条数据，开始计算")
        
        # 提取收盘价，过滤无效值
        prices = []
        for md in market_data_list:
            if md.close_price is not None and md.close_price > 0:
                prices.append(float(md.close_price))
        
        # 再次检查有效数据量（需要至少3条有效价格才能产生2个收益率样本）
        if len(prices) < 3:
            print(f"[市场数据] [稳健度计算] 数据积累中 (有效价格N={len(prices)} < 3)，返回默认值")
            return {
                "stability_score": 0.0,
                "annual_volatility": 0.0,
                "daily_returns": [],
                "remark": "数据积累中"
            }
        
        prices = np.array(prices)
        
        # 计算每日对数收益率: r_t = ln(P_t / P_{t-1})
        log_returns = np.diff(np.log(prices))
        
        # 检查收益率数据是否有效
        if len(log_returns) == 0:
            print(f"[市场数据] [稳健度计算] 无法计算收益率，数据积累中，返回默认值")
            return {
                "stability_score": 0.0,
                "annual_volatility": 0.0,
                "daily_returns": [],
                "remark": "数据积累中"
            }
        
        # 计算年化波动率: σ_annual = std(r) × sqrt(252)
        # 252 是A股每年的交易日数
        # 使用 ddof=1 进行无偏估计
        annual_volatility = float(np.std(log_returns, ddof=1) * np.sqrt(252) * 100)  # 转换为百分比
        
        # 计算稳健性评分: stability_score = max(0, 100 * (1 - σ_annual))
        # 注意：σ_annual 已经是百分比，所以需要除以100
        stability_score = float(max(0, 100 * (1 - annual_volatility / 100)))
        
        # 获取最近20个交易日的每日收益率（转换为百分比）
        # 使用简单收益率而不是对数收益率，更直观
        daily_returns_pct = []
        for i in range(max(0, len(prices) - 20), len(prices)):
            if i > 0 and prices[i-1] > 0:
                simple_return = (prices[i] - prices[i-1]) / prices[i-1] * 100
                daily_returns_pct.append(float(simple_return))
        
        print(f"[市场数据] [稳健度计算] 计算完成: 年化波动率={annual_volatility:.2f}%, 稳健性评分={stability_score:.2f}, 最近20日收益率数量={len(daily_returns_pct)}")
        
        result = {
            "stability_score": round(stability_score, 2),
            "annual_volatility": round(annual_volatility, 2),
            "daily_returns": [round(r, 2) for r in daily_returns_pct]
        }
        
        # 如果数据量较少，添加备注
        if data_count < 10:
            result["remark"] = f"数据样本较少 (N={data_count})，结果仅供参考"
        
        return result
        
    except Exception as e:
        print(f"[市场数据] [稳健度计算] 计算失败: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        # 优雅降级：返回默认值而不是 None
        return {
            "stability_score": 0.0,
            "annual_volatility": 0.0,
            "daily_returns": [],
            "remark": f"计算异常: {type(e).__name__}"
        }
