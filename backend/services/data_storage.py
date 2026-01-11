"""数据存储服务"""
from sqlalchemy.orm import Session
from datetime import date
from typing import List, Dict, Optional
import json
import time
import random

from models.asset import Asset
from models.market_data import MarketData
from services.data_fetcher import fetch_asset_data
from services.ranking_calculator import save_rankings, get_or_set_baseline_price
from config import BASELINE_DATE


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
    print(f"[数据存储] 开始存储市场数据: asset_id={asset_id}, 数据条数={len(market_data_list)}")
    
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        print(f"[数据存储] 错误: 资产不存在 (asset_id={asset_id})")
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
                    print(f"[数据存储] 已处理 {idx}/{len(market_data_list)} 条数据 (更新)")
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
                    print(f"[数据存储] 已处理 {idx}/{len(market_data_list)} 条数据 (新增)")
            
            # 如果是基准日，更新资产的基准价格
            if date_obj == baseline_date_obj and data["close_price"]:
                asset.baseline_price = data["close_price"]
                asset.baseline_date = baseline_date_obj
                print(f"[数据存储] 更新基准价格: {data['close_price']} (日期: {baseline_date_obj})")
            
        except Exception as e:
            print(f"[数据存储] 警告: 存储市场数据失败 (第 {idx} 条): {type(e).__name__}: {str(e)}")
            continue
    
    print(f"[数据存储] 提交数据库事务...")
    db.commit()
    print(f"[数据存储] 存储完成: 新增={stored_count}, 更新={updated_count}, 总计={stored_count + updated_count}")
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
    print(f"[数据更新] ========== 开始更新资产数据 (asset_id={asset_id}, force={force}) ==========")
    
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        print(f"[数据更新] 错误: 资产不存在 (asset_id={asset_id})")
        return {"success": False, "message": "资产不存在", "stored_count": 0}
    
    print(f"[数据更新] 资产信息: ID={asset.id}, 名称={asset.name}, 代码={asset.code} (原始格式), 类型={asset.asset_type}")
    
    # 确保代码格式正确（代码格式转换会在 fetch_asset_data 中自动处理）
    from services.data_fetcher import normalize_stock_code
    normalized_code = normalize_stock_code(asset.code)
    if normalized_code != asset.code:
        print(f"[数据更新] 代码格式转换: {asset.code} -> {normalized_code}")
    
    # 确定更新日期范围
    start_date = asset.start_date.isoformat() if asset.start_date else "2026-01-06"
    end_date = asset.end_date.isoformat() if asset.end_date else "2026-12-31"
    
    print(f"[数据更新] 资产配置的日期范围: {start_date} 至 {end_date}")
    
    # 检查基准日期数据是否存在
    from config import BASELINE_DATE
    from datetime import date as date_type
    baseline_date_obj = date_type.fromisoformat(BASELINE_DATE) if isinstance(BASELINE_DATE, str) else BASELINE_DATE
    
    baseline_data = db.query(MarketData).filter(
        MarketData.asset_id == asset_id,
        MarketData.date == baseline_date_obj
    ).first()
    
    need_baseline = False
    if not baseline_data:
        print(f"[数据更新] 警告: 缺少基准日期 {BASELINE_DATE} 的数据，需要补全")
        need_baseline = True
    
    # 如果不需要强制更新，检查最新数据日期
    if not force:
        latest_data = db.query(MarketData).filter(
            MarketData.asset_id == asset_id
        ).order_by(MarketData.date.desc()).first()
        
        if latest_data:
            # 从最新数据日期之后开始更新
            from datetime import timedelta
            start_date = (latest_data.date + timedelta(days=1)).isoformat()
            print(f"[数据更新] 检测到已有最新数据日期: {latest_data.date}, 将从 {start_date} 开始更新")
        else:
            print(f"[数据更新] 未检测到已有数据，将从配置的开始日期更新")
    else:
        print(f"[数据更新] 强制更新模式，将更新整个日期范围")
    
    # 如果需要补全基准数据，先获取基准日期的数据
    baseline_stored_count = 0
    if need_baseline:
        print(f"[数据更新] 补全基准日期 {BASELINE_DATE} 的数据...")
        baseline_data_list = fetch_asset_data(
            code=asset.code,
            asset_type=asset.asset_type,
            start_date=BASELINE_DATE,
            end_date=BASELINE_DATE
        )
        if baseline_data_list:
            baseline_stored_count = store_market_data(asset_id, baseline_data_list, db)
            print(f"[数据更新] 基准日期数据补全完成，存储了 {baseline_stored_count} 条数据")
        else:
            print(f"[数据更新] 警告: 无法获取基准日期数据")
    
    try:
        print(f"[数据更新] 调用 fetch_asset_data 获取数据...")
        # 获取数据
        market_data_list = fetch_asset_data(
            code=asset.code,
            asset_type=asset.asset_type,
            start_date=start_date,
            end_date=end_date
        )
        
        print(f"[数据更新] fetch_asset_data 返回 {len(market_data_list) if market_data_list else 0} 条数据")
        
        if not market_data_list:
            print(f"[数据更新] 警告: 未获取到数据")
            return {"success": False, "message": "未获取到数据", "stored_count": 0}
        
        print(f"[数据更新] 开始存储数据到数据库...")
        # 存储数据
        stored_count = store_market_data(asset_id, market_data_list, db)
        print(f"[数据更新] 成功存储 {stored_count} 条数据（包含基准日期 {baseline_stored_count} 条）")
        
        print(f"[数据更新] 更新基准价格...")
        # 更新基准价格
        get_or_set_baseline_price(asset, db)
        
        total_stored = stored_count + baseline_stored_count
        print(f"[数据更新] ========== 资产数据更新完成 (asset_id={asset_id}) ==========")
        return {
            "success": True,
            "message": f"成功更新 {total_stored} 条数据（新增 {stored_count} 条，基准日期 {baseline_stored_count} 条）",
            "stored_count": total_stored
        }
    except Exception as e:
        print(f"[数据更新] 错误: 更新资产数据失败 (asset_id={asset_id}): {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[数据更新] 错误堆栈:\n{traceback.format_exc()}")
        db.rollback()
        return {"success": False, "message": f"更新失败: {str(e)}", "stored_count": 0}


def update_all_assets_data(db: Session, force: bool = False) -> Dict:
    """更新所有资产数据"""
    print(f"[数据更新] ========== 开始批量更新所有资产数据 (force={force}) ==========")
    
    assets = db.query(Asset).all()
    print(f"[数据更新] 找到 {len(assets)} 个资产需要更新")
    
    results = {
        "total": len(assets),
        "success": 0,
        "failed": 0,
        "details": []
    }
    
    for idx, asset in enumerate(assets, 1):
        print(f"[数据更新] -------- 处理资产 {idx}/{len(assets)}: {asset.name} (ID: {asset.id}) --------")
        
        # 在资产之间添加随机延迟（1-3秒），降低被封 IP 的风险
        if idx > 1:  # 第一个资产不需要延迟
            delay = random.uniform(1, 3)
            print(f"[数据更新] 随机延迟 {delay:.2f} 秒，降低 IP 频率限制风险...")
            time.sleep(delay)
        
        try:
            result = update_asset_data(asset.id, db, force)
            if result["success"]:
                results["success"] += 1
                print(f"[数据更新] ✓ 资产 {asset.name} 更新成功")
            else:
                results["failed"] += 1
                print(f"[数据更新] ✗ 资产 {asset.name} 更新失败: {result.get('message', '未知错误')}")
            results["details"].append({
                "asset_id": asset.id,
                "asset_name": asset.name,
                "result": result
            })
        except Exception as e:
            # 单个资产失败不应该导致整个批量更新崩溃
            results["failed"] += 1
            error_msg = f"处理资产时发生异常: {type(e).__name__}: {str(e)}"
            print(f"[数据更新] ✗ 资产 {asset.name} 处理异常: {error_msg}")
            import traceback
            print(f"[数据更新] 完整错误堆栈:\n{traceback.format_exc()}")
            results["details"].append({
                "asset_id": asset.id,
                "asset_name": asset.name,
                "result": {
                    "success": False,
                    "message": error_msg,
                    "stored_count": 0
                }
            })
    
    print(f"[数据更新] ========== 批量更新完成: 总计={results['total']}, 成功={results['success']}, 失败={results['failed']} ==========")
    return results
