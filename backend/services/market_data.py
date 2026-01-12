"""市场数据服务
专门存放调用外部接口（如 yfinance）获取市场数据的逻辑
"""
import pandas as pd
from datetime import date, timedelta
from typing import Optional, Dict, List
import json
import time
import random
import traceback

from sqlalchemy.orm import Session
from database.models import Asset, MarketData
from config import BASELINE_DATE

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
        print(f"[市场数据] yfinance 不可用")
        return None
    
    try:
        print(f"[市场数据] [yfinance] 尝试获取数据: code={code}")
        
        # 转换为 yfinance 格式
        symbol = convert_to_yfinance_symbol(code)
        print(f"[市场数据] [yfinance] 转换后的符号: {symbol}")
        
        # 使用 yfinance 获取数据
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date)
        
        if df is None or df.empty:
            print(f"[市场数据] [yfinance] 未获取到数据")
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
            # 转换日期格式（baostock 需要 YYYYMMDD）
            start_dt = start_date.replace("-", "")
            end_dt = end_date.replace("-", "")
            
            # 获取数据
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,preclose,volume,amount,adjustflag,turn,pctChg,isST",
                start_date=start_dt,
                end_date=end_dt,
                frequency="d",
                adjustflag="3"  # 前复权
            )
            
            if rs.error_code != '0':
                print(f"[市场数据] [baostock] 查询失败: {rs.error_msg}")
                return None
            
            # 转换为 DataFrame
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
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
    
    # 1. 优先尝试 yfinance
    df = fetch_stock_data_yfinance(code, start_date, end_date)
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
        print(f"[市场数据] 解析市场数据时出错: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
    
    return results


def fetch_asset_data(
    code: str,
    asset_type: str,
    start_date: str,
    end_date: str
) -> List[Dict]:
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
    print(f"[市场数据] ===== 开始获取资产数据 =====")
    print(f"[市场数据] 资产代码: {code}")
    print(f"[市场数据] 资产类型: {asset_type}")
    print(f"[市场数据] 日期范围: {start_date} 至 {end_date}")
    
    try:
        df = None
        if asset_type == "stock":
            df = fetch_stock_data(code, start_date, end_date)
        elif asset_type == "fund":
            df = fetch_fund_data(code, start_date, end_date)
        else:
            print(f"[市场数据] 错误: 不支持的资产类型: {asset_type}")
            return []
        
        if df is None or df.empty:
            print(f"[市场数据] ===== 未获取到数据，返回空列表 =====")
            return []
        
        print(f"[市场数据] 开始解析市场数据...")
        result = parse_market_data(df, asset_type, code)
        print(f"[市场数据] ===== 成功解析 {len(result)} 条数据 =====")
        
        return result
    except Exception as e:
        print(f"[市场数据] 错误: 获取资产数据时发生异常: {type(e).__name__}: {str(e)}")
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
            
            # 检查是否已存在
            existing = db.query(MarketData).filter(
                MarketData.asset_id == asset_id,
                MarketData.date == date_obj
            ).first()
            
            if existing:
                # 更新现有数据
                existing.close_price = data["close_price"]
                existing.volume = data.get("volume")
                existing.turnover_rate = data.get("turnover_rate")
                existing.pe_ratio = data.get("pe_ratio")
                existing.market_cap = data.get("market_cap")
                if data.get("additional_data"):
                    existing.additional_data = json.dumps(data["additional_data"], ensure_ascii=False)
                updated_count += 1
                if idx % 50 == 0:
                    print(f"[市场数据] 已处理 {idx}/{len(market_data_list)} 条数据 (更新)")
            else:
                # 创建新数据
                market_data = MarketData(
                    asset_id=asset_id,
                    date=date_obj,
                    close_price=data["close_price"],
                    volume=data.get("volume"),
                    turnover_rate=data.get("turnover_rate"),
                    pe_ratio=data.get("pe_ratio"),
                    market_cap=data.get("market_cap"),
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
    更新资产数据
    
    Args:
        asset_id: 资产ID
        db: 数据库会话
        force: 是否强制更新（即使已有数据）
    
    Returns:
        {"success": bool, "message": str, "stored_count": int}
    """
    print(f"[市场数据] ========== 开始更新资产数据 (asset_id={asset_id}, force={force}) ==========")
    
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        print(f"[市场数据] 错误: 资产不存在 (asset_id={asset_id})")
        return {"success": False, "message": "资产不存在", "stored_count": 0}
    
    print(f"[市场数据] 资产信息: ID={asset.id}, 名称={asset.name}, 代码={asset.code} (原始格式), 类型={asset.asset_type}")
    
    # 确保代码格式正确
    normalized_code = normalize_stock_code(asset.code)
    if normalized_code != asset.code:
        print(f"[市场数据] 代码格式转换: {asset.code} -> {normalized_code}")
    
    # 确定更新日期范围
    start_date = asset.start_date.isoformat() if asset.start_date else "2026-01-05"
    end_date = asset.end_date.isoformat() if asset.end_date else "2026-12-31"
    
    print(f"[市场数据] 资产配置的日期范围: {start_date} 至 {end_date}")
    
    # 检查基准日期数据是否存在
    baseline_date_obj = date.fromisoformat(BASELINE_DATE) if isinstance(BASELINE_DATE, str) else BASELINE_DATE
    
    baseline_data = db.query(MarketData).filter(
        MarketData.asset_id == asset_id,
        MarketData.date == baseline_date_obj
    ).first()
    
    need_baseline = False
    if not baseline_data:
        print(f"[市场数据] 警告: 缺少基准日期 {BASELINE_DATE} 的数据，需要补全")
        need_baseline = True
    
    # 如果不需要强制更新，检查最新数据日期
    if not force:
        latest_data = db.query(MarketData).filter(
            MarketData.asset_id == asset_id
        ).order_by(MarketData.date.desc()).first()
        
        if latest_data:
            # 从最新数据日期之后开始更新
            start_date = (latest_data.date + timedelta(days=1)).isoformat()
            print(f"[市场数据] 检测到已有最新数据日期: {latest_data.date}, 将从 {start_date} 开始更新")
        else:
            print(f"[市场数据] 未检测到已有数据，将从配置的开始日期更新")
    else:
        print(f"[市场数据] 强制更新模式，将更新整个日期范围")
    
    # 如果需要补全基准数据，先获取基准日期的数据
    baseline_stored_count = 0
    if need_baseline:
        print(f"[市场数据] 补全基准日期 {BASELINE_DATE} 的数据...")
        baseline_data_list = fetch_asset_data(
            code=asset.code,
            asset_type=asset.asset_type,
            start_date=BASELINE_DATE,
            end_date=BASELINE_DATE
        )
        if baseline_data_list:
            baseline_stored_count = store_market_data(asset_id, baseline_data_list, db)
            print(f"[市场数据] 基准日期数据补全完成，存储了 {baseline_stored_count} 条数据")
        else:
            print(f"[市场数据] 警告: 无法获取基准日期数据")
    
    try:
        print(f"[市场数据] 调用 fetch_asset_data 获取数据...")
        # 获取数据
        market_data_list = fetch_asset_data(
            code=asset.code,
            asset_type=asset.asset_type,
            start_date=start_date,
            end_date=end_date
        )
        
        print(f"[市场数据] fetch_asset_data 返回 {len(market_data_list) if market_data_list else 0} 条数据")
        
        if not market_data_list:
            print(f"[市场数据] 警告: 未获取到数据")
            return {"success": False, "message": "未获取到数据", "stored_count": 0}
        
        print(f"[市场数据] 开始存储数据到数据库...")
        # 存储数据
        stored_count = store_market_data(asset_id, market_data_list, db)
        print(f"[市场数据] 成功存储 {stored_count} 条数据（包含基准日期 {baseline_stored_count} 条）")
        
        total_stored = stored_count + baseline_stored_count
        print(f"[市场数据] ========== 资产数据更新完成 (asset_id={asset_id}) ==========")
        return {
            "success": True,
            "message": f"成功更新 {total_stored} 条数据（新增 {stored_count} 条，基准日期 {baseline_stored_count} 条）",
            "stored_count": total_stored
        }
    except Exception as e:
        print(f"[市场数据] 错误: 更新资产数据失败 (asset_id={asset_id}): {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        db.rollback()
        return {"success": False, "message": f"更新失败: {str(e)}", "stored_count": 0}


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
                    "stored_count": 0
                }
            })
    
    print(f"[市场数据] ========== 批量更新完成: 总计={results['total']}, 成功={results['success']}, 失败={results['failed']} ==========")
    return results
