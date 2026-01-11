"""数据获取服务（akshare集成）"""
import akshare as ak
import pandas as pd
from datetime import date, datetime
from typing import Optional, Dict, Any
import json
import time

from config import BASELINE_DATE


def fetch_stock_data(code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    获取A股股票数据
    
    Args:
        code: 股票代码，如 "300857" 或 "600580"
        start_date: 开始日期 "YYYYMMDD"
        end_date: 结束日期 "YYYYMMDD"
    """
    try:
        # 处理代码格式（去掉市场前缀）
        clean_code = code.replace("SZ", "").replace("SH", "")
        
        # akshare获取股票历史数据
        df = ak.stock_zh_a_hist(
            symbol=clean_code,
            period="daily",
            start_date=start_date.replace("-", ""),
            end_date=end_date.replace("-", ""),
            adjust=""
        )
        
        if df is None or df.empty:
            return None
        
        # 重命名列
        df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'turnover', 'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
        
        return df
    except Exception as e:
        print(f"获取股票数据失败 {code}: {e}")
        return None


def fetch_fund_data(code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    获取基金/ETF数据
    
    Args:
        code: 基金代码，如 "513010"
        start_date: 开始日期 "YYYY-MM-DD"
        end_date: 结束日期 "YYYY-MM-DD"
    """
    try:
        # 处理代码格式
        clean_code = code.replace("SZ", "").replace("SH", "")
        
        # akshare获取ETF历史数据
        df = ak.fund_etf_hist_sina(symbol=clean_code)
        
        if df is None or df.empty:
            return None
        
        # 筛选日期范围
        df['date'] = pd.to_datetime(df['date'])
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        df = df[(df['date'] >= start) & (df['date'] <= end)]
        
        return df
    except Exception as e:
        print(f"获取基金数据失败 {code}: {e}")
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
        code: 资产代码
        asset_type: 资产类型 (stock, fund, futures, forex)
        start_date: 开始日期 "YYYY-MM-DD"
        end_date: 结束日期 "YYYY-MM-DD"
    
    Returns:
        list of market data dicts
    """
    # 转换日期格式
    start_dt = start_date.replace("-", "")
    end_dt = end_date.replace("-", "")
    
    df = None
    if asset_type == "stock":
        df = fetch_stock_data(code, start_date, end_date)
    elif asset_type == "fund":
        df = fetch_fund_data(code, start_date, end_date)
    # 其他类型待实现
    # elif asset_type == "futures":
    #     df = fetch_futures_data(code, start_date, end_date)
    # elif asset_type == "forex":
    #     df = fetch_forex_data(code, start_date, end_date)
    
    if df is None:
        return []
    
    return parse_market_data(df, asset_type, code)
