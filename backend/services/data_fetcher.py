"""数据获取服务（yfinance主数据源，baostock备份）"""
import pandas as pd
from datetime import date, datetime
from typing import Optional, Dict, Any
import json
import time
import traceback

# 尝试导入 yfinance
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("[数据获取] 警告: yfinance 未安装")

# 尝试导入 baostock
try:
    import baostock as bs
    BAOSTOCK_AVAILABLE = True
except ImportError:
    BAOSTOCK_AVAILABLE = False
    print("[数据获取] 警告: baostock 未安装")

from config import BASELINE_DATE


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
        print(f"[数据获取] 警告: 无法识别代码 {clean_code} 的市场，默认使用上海市场")
        return f"{clean_code}.SS"


def fetch_stock_data_yfinance(code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    使用 yfinance 获取A股股票数据（主数据源）
    
    Args:
        code: 股票代码（支持多种格式）
        start_date: 开始日期 "YYYY-MM-DD"
        end_date: 结束日期 "YYYY-MM-DD"
    
    Returns:
        pd.DataFrame 或 None（失败时）
    """
    if not YFINANCE_AVAILABLE:
        print(f"[数据获取] yfinance 不可用")
        return None
    
    try:
        print(f"[数据获取] [yfinance] 尝试获取数据: code={code}")
        
        # 转换为 yfinance 格式
        symbol = convert_to_yfinance_symbol(code)
        print(f"[数据获取] [yfinance] 转换后的符号: {symbol}")
        
        # 使用 yfinance 获取数据
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date)
        
        if df is None or df.empty:
            print(f"[数据获取] [yfinance] 未获取到数据")
            return None
        
        print(f"[数据获取] [yfinance] 成功获取 {len(df)} 条数据")
        
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
        
        print(f"[数据获取] [yfinance] 数据处理完成")
        return df
        
    except Exception as e:
        print(f"[数据获取] [yfinance] 获取数据失败: {type(e).__name__}: {str(e)}")
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
        print(f"[数据获取] [baostock] 不可用")
        return None
    
    try:
        print(f"[数据获取] [baostock] 尝试获取数据: code={code}")
        
        # 标准化代码
        clean_code = normalize_stock_code(code)
        
        # 转换为 baostock 格式（需要添加市场前缀）
        if clean_code.startswith('6'):
            bs_code = f"sh.{clean_code}"  # 上海市场
        elif clean_code.startswith(('0', '3')):
            bs_code = f"sz.{clean_code}"  # 深圳市场
        else:
            print(f"[数据获取] [baostock] 无法识别代码 {clean_code} 的市场")
            return None
        
        print(f"[数据获取] [baostock] 转换后的代码: {bs_code}")
        
        # 登录 baostock
        lg = bs.login()
        if lg.error_code != '0':
            print(f"[数据获取] [baostock] 登录失败: {lg.error_msg}")
            return None
        
        try:
            # 转换日期格式（baostock 需要 YYYYMMDD）
            start_dt = start_date.replace("-", "")
            end_dt = end_date.replace("-", "")
            
            # 获取数据
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST",
                start_date=start_dt,
                end_date=end_dt,
                frequency="d",
                adjustflag="3"  # 前复权
            )
            
            if rs.error_code != '0':
                print(f"[数据获取] [baostock] 查询失败: {rs.error_msg}")
                return None
            
            # 转换为 DataFrame
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                print(f"[数据获取] [baostock] 未获取到数据")
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
            
            print(f"[数据获取] [baostock] 成功获取 {len(df)} 条数据")
            return df
            
        finally:
            # 登出 baostock
            bs.logout()
        
    except Exception as e:
        print(f"[数据获取] [baostock] 获取数据失败: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        # 确保登出
        try:
            bs.logout()
        except:
            pass
        return None


def fetch_stock_data(code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    获取A股股票数据（主数据源：yfinance，备份：baostock）
    
    Args:
        code: 股票代码，支持多种格式：
              - SH601727, SZ300857 (前缀格式)
              - 601727.SH, 300857.SZ (后缀格式)
              - 601727, 300857 (纯数字)
        start_date: 开始日期 "YYYY-MM-DD"
        end_date: 结束日期 "YYYY-MM-DD"
    
    Returns:
        pd.DataFrame 或 None（所有数据源都失败时）
    """
    print(f"[数据获取] 开始获取股票数据: code={code}, start_date={start_date}, end_date={end_date}")
    
    # 1. 优先尝试 yfinance
    df = fetch_stock_data_yfinance(code, start_date, end_date)
    if df is not None and not df.empty:
        print(f"[数据获取] 使用 yfinance 成功获取数据")
        return df
    
    # 2. yfinance 失败，尝试 baostock
    print(f"[数据获取] yfinance 未获取到数据，尝试 baostock 备份...")
    df = fetch_stock_data_baostock(code, start_date, end_date)
    if df is not None and not df.empty:
        print(f"[数据获取] 使用 baostock 成功获取数据")
        return df
    
    # 3. 所有数据源都失败
    print(f"[数据获取] 所有数据源都未获取到数据")
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
    print(f"[数据获取] 开始获取基金数据: code={code}, start_date={start_date}, end_date={end_date}")
    
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
                print(f"[数据获取] 基金数据获取成功: {len(df)} 条")
                return df
        except Exception as e:
            print(f"[数据获取] 基金数据获取失败 (yfinance): {type(e).__name__}: {str(e)}")
    
    print(f"[数据获取] 基金数据获取失败")
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
    try:
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
            
            # 其他数据存入additional_data
            for col in df.columns:
                if col not in ['date', 'close', '净值', 'close_price', 'volume', 'turnover_rate', '换手率']:
                    if pd.notna(row[col]) and row[col] is not None:
                        try:
                            data["additional_data"][col] = float(row[col]) if isinstance(row[col], (int, float)) else str(row[col])
                        except:
                            pass
            
            if data["date"] and data["close_price"] is not None:
                results.append(data)
    except Exception as e:
        print(f"[数据获取] 解析市场数据时出错: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
    
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
        list of market data dicts（失败时返回空列表）
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
        
        if df is None or df.empty:
            print(f"[数据获取] ===== 未获取到数据，返回空列表 =====")
            return []
        
        print(f"[数据获取] 开始解析市场数据...")
        result = parse_market_data(df, asset_type, code)
        print(f"[数据获取] ===== 成功解析 {len(result)} 条数据 =====")
        
        return result
    except Exception as e:
        print(f"[数据获取] 错误: 获取资产数据时发生异常: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        # 返回空列表而不是抛出异常，让调用者可以继续处理其他资产
        return []
