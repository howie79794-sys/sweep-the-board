"""数据获取服务（akshare集成）"""
import akshare as ak
import pandas as pd
from datetime import date, datetime
from typing import Optional, Dict, Any
import json
import time
import traceback
import signal
from contextlib import contextmanager

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
        
        # akshare获取股票历史数据（添加超时处理）
        print(f"[数据获取] 调用 akshare.stock_zh_a_hist...")
        try:
            # 设置超时时间为 30 秒
            # akshare 内部使用 requests，我们通过 monkey patch 来设置超时
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
                    symbol=clean_code,
                    period="daily",
                    start_date=start_dt,
                    end_date=end_dt,
                    adjust=""
                )
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
            print(f"[数据获取] 警告: 未获取到数据，返回空结果")
            return None
        
        print(f"[数据获取] 成功获取 {len(df)} 条数据")
        
        # 重命名列
        df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'turnover', 'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
        
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
