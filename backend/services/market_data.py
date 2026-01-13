"""市场数据服务
专门存放调用外部接口（如 yfinance）获取市场数据的逻辑
"""
import pandas as pd
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Dict, List
import json
import time
import random
import traceback

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

# 尝试导入 baostock
try:
    import baostock as bs
    BAOSTOCK_AVAILABLE = True
except ImportError:
    BAOSTOCK_AVAILABLE = False
    print("[市场数据] 警告: baostock 未安装")


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


def format_date_for_baostock(date_input) -> str:
    """
    格式化日期为 baostock 需要的 YYYYMMDD 格式（8位数字，无分隔符）
    
    Args:
        date_input: 日期输入，可以是 date 对象或字符串
    
    Returns:
        str: YYYYMMDD 格式的日期字符串（8位数字）
    
    Raises:
        ValueError: 如果无法解析日期格式
    """
    if isinstance(date_input, date):
        return date_input.strftime('%Y%m%d')
    elif isinstance(date_input, str):
        # 去除所有空格、分隔符和特殊字符
        cleaned = date_input.replace("-", "").replace("/", "").replace(" ", "").replace("_", "").strip()
        # 验证是否为8位数字
        if len(cleaned) == 8 and cleaned.isdigit():
            return cleaned
        else:
            # 尝试解析为标准格式
            try:
                # 尝试多种日期格式
                for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y%m%d']:
                    try:
                        date_obj = datetime.strptime(date_input.strip(), fmt).date()
                        return date_obj.strftime('%Y%m%d')
                    except ValueError:
                        continue
                # 如果都失败，尝试使用 fromisoformat
                date_obj = date.fromisoformat(date_input.replace("/", "-").strip())
                return date_obj.strftime('%Y%m%d')
            except Exception as e:
                raise ValueError(f"无法解析日期格式: {date_input} (错误: {str(e)})")
    else:
        raise ValueError(f"不支持的日期类型: {type(date_input)}")


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
            # 转换日期格式（baostock 需要 YYYYMMDD，必须是8位数字）
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
        target_date_str = target_date.strftime('%Y-%m-%d')
        
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
            
            # 如果数据库中没有数据，尝试回溯日期（最多回溯30天）
            print(f"[市场数据] [回退机制] 数据库中没有找到数据，尝试从外部API回溯...")
            for days_back in range(1, 31):
                fallback_date = today - timedelta(days=days_back)
                fallback_date_str = fallback_date.strftime('%Y-%m-%d')
                
                print(f"[市场数据] [回退机制] 尝试回溯 {days_back} 天: {fallback_date_str}")
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
    print(f"[市场数据] 开始获取股票数据: code={code}, start_date={start_date}, end_date={end_date}")
    
    beijing_time = get_beijing_time()
    today_str = beijing_time.strftime('%Y-%m-%d')
    in_trading_hours = is_trading_hours()
    
    # 如果查询的是今天的数据且在交易时间内，尝试获取实时价格
    if end_date >= today_str and in_trading_hours:
        print(f"[市场数据] 盘中交易时间，尝试获取实时价格")
        df = fetch_stock_data_yfinance(code, start_date, end_date, use_realtime=True)
        if df is not None and not df.empty:
            print(f"[市场数据] 使用 yfinance 实时价格成功获取数据")
            return df
    
    # 1. 优先尝试 yfinance（收盘数据）
    df = fetch_stock_data_yfinance(code, start_date, end_date, use_realtime=False)
    if df is not None and not df.empty:
        print(f"[市场数据] 使用 yfinance 成功获取数据")
        return df
    
    # 2. yfinance 失败，尝试 baostock
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
    获取基金/ETF数据
    基金数据暂时使用 yfinance 或 baostock，后续可以根据需要扩展
    
    Args:
        code: 基金代码
        start_date: 开始日期 "YYYY-MM-DD"
        end_date: 结束日期 "YYYY-MM-DD"
    
    Returns:
        pd.DataFrame 或 None（失败时）
    """
    print(f"[市场数据] 开始获取基金数据: code={code}, start_date={start_date}, end_date={end_date}")
    
    # 基金数据暂时使用股票数据的获取方式（ETF 可以用 yfinance）
    # 尝试 yfinance
    if YFINANCE_AVAILABLE:
        try:
            # 转换为 yfinance 格式
            symbol = convert_to_yfinance_symbol(code)
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            
            if df is not None and not df.empty:
                df = df.reset_index()
                column_mapping = {
                    'Date': 'date',
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                }
                df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                
                # 添加缺失的列
                expected_cols = ['date', 'open', 'close', 'high', 'low', 'volume', 'turnover', 'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
                for col in expected_cols:
                    if col not in df.columns:
                        df[col] = None
                df = df[expected_cols]
                print(f"[市场数据] 基金数据获取成功: {len(df)} 条")
                return df
        except Exception as e:
            print(f"[市场数据] 基金数据获取失败 (yfinance): {type(e).__name__}: {str(e)}")
    
    print(f"[市场数据] 基金数据获取失败")
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
                    data["date"] = row['date']
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


def fetch_asset_data(
    code: str,
    asset_type: str,
    start_date: str,
    end_date: str,
    db: Optional[Session] = None
) -> List[Dict]:
    """
    获取资产数据（统一接口）
    
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
    print(f"[市场数据] 日期范围: {start_date} 至 {end_date}")
    
    try:
        df = None
        try:
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
            
            # 如果查询的是今天的数据，且是股票类型，且有数据库会话，使用回退机制
            if asset_type == "stock" and end_date_obj == today and db is not None:
                print(f"[市场数据] 查询今天的数据，使用回退机制")
                try:
                    df = fetch_stock_data_with_fallback(code, today, db)
                except Exception as e:
                    print(f"[市场数据] 错误: 回退机制执行时发生异常: {type(e).__name__}: {str(e)}")
                    traceback.print_exc()
                    df = None
            elif asset_type == "stock":
                try:
                    df = fetch_stock_data(code, start_date, end_date)
                except Exception as e:
                    print(f"[市场数据] 错误: 获取股票数据时发生异常: {type(e).__name__}: {str(e)}")
                    traceback.print_exc()
                    df = None
            elif asset_type == "fund":
                try:
                    df = fetch_fund_data(code, start_date, end_date)
                except Exception as e:
                    print(f"[市场数据] 错误: 获取基金数据时发生异常: {type(e).__name__}: {str(e)}")
                    traceback.print_exc()
                    df = None
            else:
                print(f"[市场数据] 错误: 不支持的资产类型: {asset_type}")
                return []
        except TimeoutError as e:
            print(f"[市场数据] 错误: 获取资产数据超时: {str(e)}")
            traceback.print_exc()
            return []
        except ValueError as e:
            print(f"[市场数据] 错误: 值错误: {str(e)}")
            traceback.print_exc()
            return []
        except Exception as e:
            print(f"[市场数据] 错误: 获取资产数据时发生未预期的异常: {type(e).__name__}: {str(e)}")
            traceback.print_exc()
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


def update_asset_data(asset_id: int, db: Session, force: bool = False) -> Dict:
    """
    更新资产数据 - 自动补全历史缺失数据
    
    Args:
        asset_id: 资产ID
        db: 数据库会话
        force: 是否强制更新（即使已有数据）
    
    Returns:
        {"success": bool, "message": str, "stored_count": int, "new_data_count": int, "filled_metrics_count": int}
    """
    print(f"[市场数据] ========== 开始更新资产数据 (asset_id={asset_id}, force={force}) ==========")
    
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        print(f"[市场数据] 错误: 资产不存在 (asset_id={asset_id})")
        return {"success": False, "message": "资产不存在", "stored_count": 0, "new_data_count": 0, "filled_metrics_count": 0}
    
    print(f"[市场数据] 资产信息: ID={asset.id}, 名称={asset.name}, 代码={asset.code}, 类型={asset.asset_type}")
    
    # 确定扫描日期范围：从基准日期到今天
    baseline_date_obj = date.fromisoformat(BASELINE_DATE) if isinstance(BASELINE_DATE, str) else BASELINE_DATE
    today = date.today()
    
    print(f"[市场数据] 扫描日期范围: {baseline_date_obj} 至 {today}")
    
    # 获取最新的财务指标（作为基准用于反推）
    # 查找有完整财务指标的最新记录
    latest_with_metrics = db.query(MarketData).filter(
        MarketData.asset_id == asset_id,
        MarketData.pe_ratio.isnot(None),
        MarketData.pe_ratio != 0
    ).order_by(MarketData.date.desc()).first()
    
    # 如果没有找到有财务指标的记录，尝试获取最新的记录（可能只有价格）
    if not latest_with_metrics:
        latest_with_metrics = db.query(MarketData).filter(
            MarketData.asset_id == asset_id
        ).order_by(MarketData.date.desc()).first()
    
    # 统计变量
    new_data_count = 0  # 新增的数据记录数
    filled_metrics_count = 0  # 补全财务指标的记录数
    skipped_count = 0  # 跳过的完整记录数
    
    # 获取最新的财务指标（用于反推）
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
    
    # 如果还没有财务指标，先尝试获取最新的财务指标
    if not ref_pe and asset.asset_type == "stock":
        print(f"[市场数据] 未找到财务指标基准，尝试获取最新财务指标...")
        try:
            # 获取今天的数据（包含财务指标）
            today_data_list = fetch_asset_data(
                code=asset.code,
                asset_type=asset.asset_type,
                start_date=today.isoformat(),
                end_date=today.isoformat(),
                db=db
            )
            if today_data_list and len(today_data_list) > 0:
                today_data = today_data_list[0]
                if today_data.get("pe_ratio") and today_data.get("pe_ratio") != 0:
                    ref_pe = today_data.get("pe_ratio")
                    ref_pb = today_data.get("pb_ratio") if today_data.get("pb_ratio") else None
                    ref_market_cap = today_data.get("market_cap") if today_data.get("market_cap") and today_data.get("market_cap") > 0 else None
                    ref_eps = today_data.get("eps_forecast") if today_data.get("eps_forecast") else None
                    ref_price = today_data.get("close_price")
                    ref_date = date.fromisoformat(today_data.get("date"))
                    print(f"[市场数据] 成功获取最新财务指标: PE={ref_pe}, PB={ref_pb}, 市值={ref_market_cap}, EPS={ref_eps}")
        except Exception as e:
            print(f"[市场数据] 获取最新财务指标失败: {str(e)}")
    
    # 遍历日期范围内的每一天
    current_date = baseline_date_obj
    while current_date <= today:
        try:
            # 检查该日期是否已存在记录
            existing_record = db.query(MarketData).filter(
                MarketData.asset_id == asset_id,
                MarketData.date == current_date
            ).first()
            
            if existing_record:
                # 检查数据是否完整
                has_price = existing_record.close_price is not None
                has_metrics = (
                    (existing_record.pe_ratio is not None and existing_record.pe_ratio != 0) or
                    (existing_record.pb_ratio is not None and existing_record.pb_ratio != 0) or
                    (existing_record.market_cap is not None and existing_record.market_cap > 0)
                )
                
                if has_price and has_metrics:
                    # 数据完整，跳过
                    skipped_count += 1
                    if skipped_count % 10 == 0:
                        print(f"[市场数据] 已跳过 {skipped_count} 条完整记录...")
                elif has_price and not has_metrics:
                    # 有价格但缺少财务指标，需要补全
                    if ref_pe and ref_price and ref_price > 0:
                        hist_price = existing_record.close_price
                        price_ratio = hist_price / ref_price
                        
                        # 根据股价波动比例反推历史指标
                        existing_record.pe_ratio = ref_pe * price_ratio
                        if ref_pb:
                            existing_record.pb_ratio = ref_pb * price_ratio
                        if ref_market_cap:
                            existing_record.market_cap = ref_market_cap * price_ratio
                        if ref_eps:
                            existing_record.eps_forecast = ref_eps  # EPS 保持不变
                        
                        filled_metrics_count += 1
                        pe_str = f"{existing_record.pe_ratio:.2f}" if existing_record.pe_ratio is not None else "N/A"
                        pb_str = f"{existing_record.pb_ratio:.2f}" if existing_record.pb_ratio is not None else "N/A"
                        market_cap_str = f"{existing_record.market_cap:.2f}" if existing_record.market_cap is not None else "N/A"
                        print(f"[市场数据] 补全财务指标 (日期: {current_date}): PE={pe_str}, PB={pb_str}, 市值={market_cap_str}")
                    else:
                        print(f"[市场数据] 警告: 日期 {current_date} 缺少财务指标，但无基准数据可反推")
            else:
                # 记录不存在，需要获取历史价格并补全财务指标
                try:
                    # 获取该日期的历史价格
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
                            
                            # 如果有基准财务指标，按比例反推
                            if ref_pe and ref_price and ref_price > 0:
                                price_ratio = hist_price / ref_price
                                market_data.pe_ratio = ref_pe * price_ratio
                                if ref_pb:
                                    market_data.pb_ratio = ref_pb * price_ratio
                                if ref_market_cap:
                                    market_data.market_cap = ref_market_cap * price_ratio
                                if ref_eps:
                                    market_data.eps_forecast = ref_eps
                                
                                pe_str = f"{market_data.pe_ratio:.2f}" if market_data.pe_ratio is not None else "N/A"
                                print(f"[市场数据] 新增记录并补全指标 (日期: {current_date}): 价格={hist_price}, PE={pe_str}")
                            else:
                                print(f"[市场数据] 新增记录 (日期: {current_date}): 价格={hist_price} (无基准指标)")
                            
                            db.add(market_data)
                            new_data_count += 1
                        else:
                            print(f"[市场数据] 警告: 日期 {current_date} 无法获取价格数据")
                    else:
                        print(f"[市场数据] 警告: 日期 {current_date} 无法获取数据")
                except Exception as e:
                    print(f"[市场数据] 警告: 获取日期 {current_date} 的数据时发生异常: {str(e)}")
        except Exception as e:
            # 单个日期处理失败不应该导致整个资产更新失败
            print(f"[市场数据] 警告: 处理日期 {current_date} 时发生异常: {type(e).__name__}: {str(e)}")
            traceback.print_exc()
        
        # 移动到下一天
        current_date += timedelta(days=1)
    
    # 提交所有更改
    try:
        db.commit()
        total_count = new_data_count + filled_metrics_count
        
        # 构建返回消息
        if new_data_count > 0 and filled_metrics_count > 0:
            message = f"成功抓取了 {new_data_count} 条新数据，补全了 {filled_metrics_count} 条历史缺失指标"
        elif new_data_count > 0:
            message = f"成功抓取了 {new_data_count} 条新数据"
        elif filled_metrics_count > 0:
            message = f"补全了 {filled_metrics_count} 条历史缺失指标"
        else:
            message = f"数据已完整，无需更新（跳过了 {skipped_count} 条完整记录）"
        
        print(f"[市场数据] ========== 资产数据更新完成 (asset_id={asset_id}) ==========")
        print(f"[市场数据] 统计: 新增={new_data_count}, 补全指标={filled_metrics_count}, 跳过={skipped_count}, 总计={total_count}")
        
        return {
            "success": True,
            "message": message,
            "stored_count": total_count,
            "new_data_count": new_data_count,
            "filled_metrics_count": filled_metrics_count
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
            "filled_metrics_count": 0
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
