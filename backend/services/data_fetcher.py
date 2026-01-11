"""数据获取服务（akshare集成，yfinance作为备用）"""
import akshare as ak
import pandas as pd
from datetime import date, datetime
from typing import Optional, Dict, Any
import json
import time
import traceback
import signal
import random
from contextlib import contextmanager

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("[数据获取] 警告: yfinance 未安装，将无法使用备用数据源")

from config import BASELINE_DATE


class TimeoutError(Exception):
    """超时异常"""
    pass


@contextmanager
def timeout(seconds):
    """超时上下文管理器"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"操作超时（{seconds}秒）")
    
    # 设置信号处理器（仅限 Unix 系统）
    if hasattr(signal, 'SIGALRM'):
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        # Windows 系统不支持 SIGALRM，使用简单实现
        yield


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
    # 去掉市场后缀 (.SH, .SZ)
    code = code.replace(".SH", "").replace(".SZ", "")
    # 去掉市场前缀 (SH, SZ)
    code = code.replace("SH", "").replace("SZ", "")
    return code


def convert_to_yfinance_symbol(code: str) -> str:
    """
    将A股代码转换为 yfinance 格式
    yfinance 使用 .SS (上海) 或 .SZ (深圳) 后缀
    """
    clean_code = normalize_stock_code(code)
    if clean_code.startswith('6'):
        return f"{clean_code}.SS"  # 上海市场
    elif clean_code.startswith(('0', '3')):
        return f"{clean_code}.SZ"  # 深圳市场
    else:
        # 默认尝试上海市场
        return f"{clean_code}.SS"


def fetch_stock_data_yfinance(code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    使用 yfinance 获取A股股票数据（备用数据源）
    
    Args:
        code: 股票代码
        start_date: 开始日期 "YYYY-MM-DD"
        end_date: 结束日期 "YYYY-MM-DD"
    """
    if not YFINANCE_AVAILABLE:
        print(f"[数据获取] yfinance 不可用，跳过备用数据源")
        return None
    
    try:
        print(f"[数据获取] 尝试使用 yfinance 备用数据源: code={code}")
        
        # 转换为 yfinance 格式
        symbol = convert_to_yfinance_symbol(code)
        print(f"[数据获取] yfinance 符号: {symbol}")
        
        # 使用 yfinance 获取数据
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date)
        
        if df is None or df.empty:
            print(f"[数据获取] yfinance 未获取到数据")
            return None
        
        print(f"[数据获取] yfinance 成功获取 {len(df)} 条数据")
        
        # 转换列名以匹配我们的格式
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
        
        df = df.rename(columns=column_mapping)
        
        # 计算需要的列
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        # 添加缺失的列（使用默认值）
        expected_cols = ['date', 'open', 'close', 'high', 'low', 'volume', 'turnover', 'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None
        
        # 只取需要的列
        df = df[expected_cols] if len(df.columns) >= len(expected_cols) else df.iloc[:, :len(expected_cols)]
        df.columns = expected_cols
        
        print(f"[数据获取] yfinance 数据处理完成")
        return df
        
    except Exception as e:
        print(f"[数据获取] yfinance 获取数据失败: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[数据获取] yfinance 错误堆栈:\n{traceback.format_exc()}")
        return None


def fetch_stock_data(code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    获取A股股票数据
    
    Args:
        code: 股票代码，支持多种格式：
              - SH601727, SZ300857 (前缀格式)
              - 601727.SH, 300857.SZ (后缀格式)
              - 601727, 300857 (纯数字)
        start_date: 开始日期 "YYYY-MM-DD" 或 "YYYYMMDD"
        end_date: 结束日期 "YYYY-MM-DD" 或 "YYYYMMDD"
    """
    try:
        print(f"[数据获取] 开始获取股票数据: code={code}, start_date={start_date}, end_date={end_date}")
        
        # 标准化代码格式（akshare 需要纯数字代码）
        clean_code = normalize_stock_code(code)
        print(f"[数据获取] 标准化后的代码: {clean_code}")
        
        # 标准化日期格式（akshare 需要 YYYYMMDD）
        start_dt = start_date.replace("-", "")
        end_dt = end_date.replace("-", "")
        print(f"[数据获取] 标准化后的日期: start={start_dt}, end={end_dt}")
        
        # akshare获取股票历史数据（添加超时处理和代码适配）
        print(f"[数据获取] 调用 akshare.stock_zh_a_hist...")
        
        def fetch_with_code(symbol_code):
            """使用指定代码获取数据"""
            try:
                # 设置超时时间为 30 秒
                import requests
                original_get = requests.get
                original_post = requests.post
                
                def patched_get(*args, **kwargs):
                    kwargs.setdefault('timeout', 30)
                    return original_get(*args, **kwargs)
                
                def patched_post(*args, **kwargs):
                    kwargs.setdefault('timeout', 30)
                    return original_post(*args, **kwargs)
                
                requests.get = patched_get
                requests.post = patched_post
                
                try:
                    df = ak.stock_zh_a_hist(
                        symbol=symbol_code,
                        period="daily",
                        start_date=start_dt,
                        end_date=end_dt,
                        adjust=""
                    )
                    return df
                finally:
                    # 恢复原始函数
                    requests.get = original_get
                    requests.post = original_post
            except TimeoutError as e:
                print(f"[数据获取] 超时错误: {str(e)}")
                raise
            except Exception as e:
                print(f"[数据获取] akshare 调用异常: {type(e).__name__}: {str(e)}")
                raise
        
        # 首先尝试使用原始代码
        df = fetch_with_code(clean_code)
        
        # 如果返回为空，尝试自动适配市场前缀
        if df is None or df.empty:
            print(f"[数据获取] 警告: 使用代码 {clean_code} 未获取到数据，尝试适配市场前缀...")
            
            # 尝试不同的代码格式
            code_variants = []
            
            # 如果代码是纯数字，尝试添加市场前缀
            if clean_code.isdigit():
                # 根据代码前缀判断市场
                if clean_code.startswith('6'):
                    # 6开头通常是上海市场
                    code_variants.append(clean_code)
                    code_variants.append(f"sh{clean_code}")
                elif clean_code.startswith(('0', '3')):
                    # 0或3开头通常是深圳市场
                    code_variants.append(clean_code)
                    code_variants.append(f"sz{clean_code}")
            else:
                # 如果代码已经有前缀，尝试去掉前缀
                if clean_code.lower().startswith('sh'):
                    code_variants.append(clean_code)
                    code_variants.append(clean_code[2:])
                elif clean_code.lower().startswith('sz'):
                    code_variants.append(clean_code)
                    code_variants.append(clean_code[2:])
                else:
                    # 尝试添加前缀
                    if clean_code.startswith('6'):
                        code_variants.append(f"sh{clean_code}")
                    elif clean_code.startswith(('0', '3')):
                        code_variants.append(f"sz{clean_code}")
            
            # 去除重复并尝试
            code_variants = list(dict.fromkeys(code_variants))  # 保持顺序的去重
            print(f"[数据获取] 尝试的代码变体: {code_variants}")
            
            for variant in code_variants:
                if variant == clean_code:
                    continue  # 已经试过了
                
                try:
                    print(f"[数据获取] 尝试代码变体: {variant}")
                    df = fetch_with_code(variant)
                    if df is not None and not df.empty:
                        print(f"[数据获取] ✓ 使用代码变体 {variant} 成功获取数据")
                        break
                except Exception as e:
                    print(f"[数据获取] 代码变体 {variant} 失败: {type(e).__name__}: {str(e)}")
                    continue
        
        if df is None or df.empty:
            print(f"[数据获取] 警告: AkShare 所有代码变体都未获取到数据，尝试备用数据源 yfinance...")
            # 尝试使用 yfinance 备用数据源
            df = fetch_stock_data_yfinance(code, start_date, end_date)
            if df is None or df.empty:
                print(f"[数据获取] 警告: 所有数据源都未获取到数据，返回空结果")
                return None
        
        print(f"[数据获取] 成功获取 {len(df)} 条数据")
        print(f"[数据获取] 数据列数: {len(df.columns)}, 列名: {list(df.columns)}")
        
        # 动态适配列数，只取前 11 列或按列名重命名
        expected_cols = ['date', 'open', 'close', 'high', 'low', 'volume', 'turnover', 'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
        
        # 确保至少有足够的列
        if len(df.columns) < len(expected_cols):
            print(f"[数据获取] 警告: 数据列数 {len(df.columns)} 少于预期 {len(expected_cols)} 列")
        
        # 只取前 11 列
        df = df.iloc[:, :len(expected_cols)]
        # 赋值列名
        df.columns = expected_cols
        
        print(f"[数据获取] 列名处理完成，最终列名: {list(df.columns)}")
        
        return df
    except Exception as e:
        print(f"[数据获取] 错误: 获取股票数据失败 {code}: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[数据获取] 错误堆栈:\n{traceback.format_exc()}")
        return None


def fetch_fund_data(code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    获取基金/ETF数据
    
    Args:
        code: 基金代码，支持多种格式：
              - SH513010, SZ513010 (前缀格式)
              - 513010.SH, 513010.SZ (后缀格式)
              - 513010 (纯数字)
        start_date: 开始日期 "YYYY-MM-DD"
        end_date: 结束日期 "YYYY-MM-DD"
    """
    try:
        print(f"[数据获取] 开始获取基金数据: code={code}, start_date={start_date}, end_date={end_date}")
        
        # 标准化代码格式
        clean_code = normalize_stock_code(code)
        print(f"[数据获取] 标准化后的代码: {clean_code}")
        
        # akshare获取ETF历史数据（添加超时处理）
        print(f"[数据获取] 调用 akshare.fund_etf_hist_sina...")
        try:
            # 设置超时时间为 30 秒
            import requests
            original_get = requests.get
            original_post = requests.post
            
            def patched_get(*args, **kwargs):
                kwargs.setdefault('timeout', 30)
                return original_get(*args, **kwargs)
            
            def patched_post(*args, **kwargs):
                kwargs.setdefault('timeout', 30)
                return original_post(*args, **kwargs)
            
            requests.get = patched_get
            requests.post = patched_post
            
            try:
                df = ak.fund_etf_hist_sina(symbol=clean_code)
            finally:
                # 恢复原始函数
                requests.get = original_get
                requests.post = original_post
        except TimeoutError as e:
            print(f"[数据获取] 超时错误: {str(e)}")
            raise
        except Exception as e:
            print(f"[数据获取] akshare 调用异常: {type(e).__name__}: {str(e)}")
            raise
        
        if df is None or df.empty:
            print(f"[数据获取] 警告: 未获取到基金数据，返回空结果")
            return None
        
        print(f"[数据获取] 成功获取 {len(df)} 条基金数据（筛选前）")
        
        # 筛选日期范围
        df['date'] = pd.to_datetime(df['date'])
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        df = df[(df['date'] >= start) & (df['date'] <= end)]
        
        print(f"[数据获取] 日期筛选后剩余 {len(df)} 条数据")
        
        return df
    except Exception as e:
        print(f"[数据获取] 错误: 获取基金数据失败 {code}: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[数据获取] 错误堆栈:\n{traceback.format_exc()}")
        return None


def parse_market_data(df: pd.DataFrame, asset_type: str, code: str) -> list:
    """
    解析市场数据为标准化格式
    
    Returns:
        list of dicts: [{date, close_price, volume, turnover_rate, ...}]
    """
    if df is None or df.empty:
        return []
    
    results = []
    for _, row in df.iterrows():
        data = {
            "date": None,
            "close_price": None,
            "volume": None,
            "turnover_rate": None,
            "pe_ratio": None,
            "market_cap": None,
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
            data["close_price"] = float(row['close'])
        elif '净值' in row:
            data["close_price"] = float(row['净值'])
        elif 'close_price' in row:
            data["close_price"] = float(row['close_price'])
        
        # 处理成交量
        if 'volume' in row:
            data["volume"] = float(row['volume']) if pd.notna(row['volume']) else None
        
        # 处理换手率
        if 'turnover_rate' in row:
            data["turnover_rate"] = float(row['turnover_rate']) if pd.notna(row['turnover_rate']) else None
        elif '换手率' in row:
            data["turnover_rate"] = float(row['换手率']) if pd.notna(row['换手率']) else None
        
        # 其他数据存入additional_data
        for col in df.columns:
            if col not in ['date', 'close', '净值', 'close_price', 'volume', 'turnover_rate', '换手率']:
                if pd.notna(row[col]):
                    try:
                        data["additional_data"][col] = float(row[col]) if isinstance(row[col], (int, float)) else str(row[col])
                    except:
                        pass
        
        if data["date"] and data["close_price"]:
            results.append(data)
    
    return results


def fetch_asset_data(
    code: str,
    asset_type: str,
    start_date: str,
    end_date: str
) -> list:
    """
    获取资产数据（统一接口）
    
    Args:
        code: 资产代码（支持多种格式：SH601727, 601727.SH, 601727 等）
        asset_type: 资产类型 (stock, fund, futures, forex)
        start_date: 开始日期 "YYYY-MM-DD"
        end_date: 结束日期 "YYYY-MM-DD"
    
    Returns:
        list of market data dicts
    """
    print(f"[数据获取] ===== 开始获取资产数据 =====")
    print(f"[数据获取] 资产代码: {code}")
    print(f"[数据获取] 资产类型: {asset_type}")
    print(f"[数据获取] 日期范围: {start_date} 至 {end_date}")
    
    try:
        df = None
        if asset_type == "stock":
            df = fetch_stock_data(code, start_date, end_date)
        elif asset_type == "fund":
            df = fetch_fund_data(code, start_date, end_date)
        else:
            print(f"[数据获取] 错误: 不支持的资产类型: {asset_type}")
            return []
        # 其他类型待实现
        # elif asset_type == "futures":
        #     df = fetch_futures_data(code, start_date, end_date)
        # elif asset_type == "forex":
        #     df = fetch_forex_data(code, start_date, end_date)
        
        if df is None:
            print(f"[数据获取] ===== 未获取到数据，返回空列表 =====")
            return []
        
        print(f"[数据获取] 开始解析市场数据...")
        result = parse_market_data(df, asset_type, code)
        print(f"[数据获取] ===== 成功解析 {len(result)} 条数据 =====")
        
        return result
    except Exception as e:
        print(f"[数据获取] 错误: 获取资产数据时发生异常: {type(e).__name__}: {str(e)}")
        print(f"[数据获取] 完整错误堆栈:\n{traceback.format_exc()}")
        # 返回空列表而不是抛出异常，让调用者可以继续处理其他资产
        return []
