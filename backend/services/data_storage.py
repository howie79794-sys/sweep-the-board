"""数据存储服务"""
from sqlalchemy.orm import Session
from datetime import date
from typing import List, Dict, Optional
import json

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
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        return 0
    
    stored_count = 0
    baseline_date_obj = date.fromisoformat(BASELINE_DATE)
    
    for data in market_data_list:
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
            
            # 如果是基准日，更新资产的基准价格
            if date_obj == baseline_date_obj and data["close_price"]:
                asset.baseline_price = data["close_price"]
                asset.baseline_date = baseline_date_obj
            
            stored_count += 1
        except Exception as e:
            print(f"存储市场数据失败: {e}")
            continue
    
    db.commit()
    return stored_count


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
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        return {"success": False, "message": "资产不存在", "stored_count": 0}
    
    # 确定更新日期范围
    start_date = asset.start_date.isoformat() if asset.start_date else "2026-01-06"
    end_date = asset.end_date.isoformat() if asset.end_date else "2026-12-31"
    
    # 如果不需要强制更新，检查最新数据日期
    if not force:
        latest_data = db.query(MarketData).filter(
            MarketData.asset_id == asset_id
        ).order_by(MarketData.date.desc()).first()
        
        if latest_data:
            # 从最新数据日期之后开始更新
            from datetime import timedelta
            start_date = (latest_data.date + timedelta(days=1)).isoformat()
    
    try:
        # 获取数据
        market_data_list = fetch_asset_data(
            code=asset.code,
            asset_type=asset.asset_type,
            start_date=start_date,
            end_date=end_date
        )
        
        if not market_data_list:
            return {"success": False, "message": "未获取到数据", "stored_count": 0}
        
        # 存储数据
        stored_count = store_market_data(asset_id, market_data_list, db)
        
        # 更新基准价格
        get_or_set_baseline_price(asset, db)
        
        return {
            "success": True,
            "message": f"成功更新 {stored_count} 条数据",
            "stored_count": stored_count
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"更新失败: {str(e)}", "stored_count": 0}


def update_all_assets_data(db: Session, force: bool = False) -> Dict:
    """更新所有资产数据"""
    assets = db.query(Asset).all()
    
    results = {
        "total": len(assets),
        "success": 0,
        "failed": 0,
        "details": []
    }
    
    for asset in assets:
        result = update_asset_data(asset.id, db, force)
        if result["success"]:
            results["success"] += 1
        else:
            results["failed"] += 1
        results["details"].append({
            "asset_id": asset.id,
            "asset_name": asset.name,
            "result": result
        })
    
    return results
