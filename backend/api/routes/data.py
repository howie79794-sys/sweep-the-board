"""数据管理路由"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import date, datetime

from database.base import get_db
from models.asset import Asset
from models.market_data import MarketData

router = APIRouter()


class DataUpdateRequest(BaseModel):
    """数据更新请求模型"""
    asset_ids: Optional[List[int]] = Field(
        default=None,
        description="要更新的资产ID列表，如果为null或空数组则更新所有资产"
    )
    force: bool = Field(default=False, description="是否强制更新（即使已有数据）")
    
    class Config:
        # Pydantic v1 配置
        json_schema_extra = {
            "example": {
                "asset_ids": None,
                "force": False
            }
        }


class MarketDataResponse(BaseModel):
    id: int
    asset_id: int
    date: str
    close_price: float
    volume: Optional[float]
    turnover_rate: Optional[float]
    pe_ratio: Optional[float]
    market_cap: Optional[float]
    additional_data: Optional[dict]
    created_at: str

    class Config:
        from_attributes = True


@router.get("/assets/{asset_id}")
async def get_asset_data(
    asset_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取资产的市场数据（历史）"""
    # 验证资产存在
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    query = db.query(MarketData).filter(MarketData.asset_id == asset_id)
    
    if start_date:
        query = query.filter(MarketData.date >= date.fromisoformat(start_date))
    if end_date:
        query = query.filter(MarketData.date <= date.fromisoformat(end_date))
    
    data_list = query.order_by(MarketData.date.desc()).limit(limit).all()
    
    # 转换additional_data JSON字符串为字典
    result = []
    for data in data_list:
        data_dict = {
            "id": data.id,
            "asset_id": data.asset_id,
            "date": data.date.isoformat(),
            "close_price": data.close_price,
            "volume": data.volume,
            "turnover_rate": data.turnover_rate,
            "pe_ratio": data.pe_ratio,
            "market_cap": data.market_cap,
            "additional_data": None,
            "created_at": data.created_at.isoformat() if data.created_at else None
        }
        if data.additional_data:
            import json
            try:
                data_dict["additional_data"] = json.loads(data.additional_data)
            except:
                pass
        result.append(data_dict)
    
    return result


@router.get("/assets/{asset_id}/latest")
async def get_latest_data(asset_id: int, db: Session = Depends(get_db)):
    """获取资产最新数据"""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    latest = db.query(MarketData).filter(
        MarketData.asset_id == asset_id
    ).order_by(MarketData.date.desc()).first()
    
    if not latest:
        return None
    
    result = {
        "id": latest.id,
        "asset_id": latest.asset_id,
        "date": latest.date.isoformat(),
        "close_price": latest.close_price,
        "volume": latest.volume,
        "turnover_rate": latest.turnover_rate,
        "pe_ratio": latest.pe_ratio,
        "market_cap": latest.market_cap,
        "additional_data": None,
        "created_at": latest.created_at.isoformat() if latest.created_at else None
    }
    
    if latest.additional_data:
        import json
        try:
            result["additional_data"] = json.loads(latest.additional_data)
        except:
            pass
    
    return result


@router.get("/assets/{asset_id}/baseline")
async def get_baseline_price(asset_id: int, db: Session = Depends(get_db)):
    """获取资产基准价格"""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    if asset.baseline_price is None:
        return None
    
    return {
        "baseline_price": asset.baseline_price,
        "baseline_date": asset.baseline_date.isoformat() if asset.baseline_date else None
    }


@router.post("/update")
async def trigger_update(
    request: DataUpdateRequest,
    db: Session = Depends(get_db)
):
    """触发数据更新（支持全部或指定资产）"""
    print(f"[API] ========== 收到数据更新请求 ==========")
    print(f"[API] Received data: {request}")
    print(f"[API] 请求体类型: {type(request)}")
    print(f"[API] 请求体内容: asset_ids={request.asset_ids} (类型: {type(request.asset_ids)}), force={request.force}")
    
    # 验证请求数据
    if request.asset_ids is not None and not isinstance(request.asset_ids, list):
        print(f"[API] 错误: asset_ids 不是列表类型，实际类型: {type(request.asset_ids)}")
        raise HTTPException(
            status_code=422,
            detail=f"asset_ids 必须是列表或 null，当前类型: {type(request.asset_ids).__name__}"
        )
    
    from services.data_storage import update_asset_data, update_all_assets_data
    from services.ranking_calculator import save_rankings
    from datetime import date
    
    # 处理 asset_ids：None、空列表或有效列表
    asset_ids = request.asset_ids if request.asset_ids else None
    force = request.force
    
    print(f"[API] 解析后的参数: asset_ids={asset_ids} (类型: {type(asset_ids)}), force={force}")
    
    try:
        # 如果 asset_ids 不为 None 且不为空列表，则更新指定资产
        if asset_ids and len(asset_ids) > 0:
            print(f"[API] 更新指定资产: {asset_ids}")
            # 更新指定资产
            results = []
            for asset_id in asset_ids:
                print(f"[API] 处理资产 ID: {asset_id}")
                result = update_asset_data(asset_id, db, force)
                results.append({
                    "asset_id": asset_id,
                    **result
                })
            
            print(f"[API] 开始计算排名...")
            # 计算排名
            today = date.today()
            save_rankings(today, db)
            print(f"[API] 排名计算完成")
            
            response = {
                "message": "数据更新完成",
                "results": results
            }
            print(f"[API] ========== 数据更新请求完成 ==========")
            return response
        else:
            print(f"[API] 更新所有资产")
            # 更新所有资产（外层包裹异常捕获，确保单个资产失败不会导致整个接口崩溃）
            try:
                result = update_all_assets_data(db, force)
            except Exception as e:
                print(f"[API] 错误: 批量更新资产数据时发生异常: {type(e).__name__}: {str(e)}")
                import traceback
                print(f"[API] 错误堆栈:\n{traceback.format_exc()}")
                # 返回部分结果，而不是抛出异常
                result = {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "details": [],
                    "error": f"批量更新过程中发生错误: {str(e)}"
                }
            
            print(f"[API] 开始计算排名...")
            # 计算排名（也包裹异常捕获）
            try:
                today = date.today()
                save_rankings(today, db)
                print(f"[API] 排名计算完成")
            except Exception as e:
                print(f"[API] 警告: 计算排名时发生错误: {type(e).__name__}: {str(e)}")
                import traceback
                print(f"[API] 错误堆栈:\n{traceback.format_exc()}")
                # 排名计算失败不影响数据更新结果
            
            response = {
                "message": "所有资产数据更新完成",
                **result
            }
            print(f"[API] ========== 数据更新请求完成 ==========")
            return response
    except Exception as e:
        print(f"[API] 错误: 数据更新请求处理失败: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[API] 完整错误堆栈:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"数据更新失败: {str(e)}")


@router.get("/markets/types")
async def get_market_types():
    """获取支持的市场类型列表"""
    return {
        "asset_types": ["stock", "fund", "futures", "forex"],
        "markets": {
            "stock": ["A股", "港股", "美股"],
            "fund": ["A股基金", "ETF"],
            "futures": ["国内期货", "国际期货"],
            "forex": ["主要货币对"]
        }
    }
