"""资产管理路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import date, datetime

from database.base import get_db
from models.asset import Asset
from models.user import User

router = APIRouter()


class AssetCreate(BaseModel):
    user_id: int
    asset_type: str  # stock, fund, futures, forex
    market: str
    code: str
    name: str
    baseline_date: Optional[str] = "2026-01-05"
    start_date: Optional[str] = "2026-01-05"
    end_date: Optional[str] = "2026-12-31"


class AssetUpdate(BaseModel):
    user_id: Optional[int] = None
    asset_type: Optional[str] = None
    market: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    baseline_price: Optional[float] = None
    baseline_date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class AssetResponse(BaseModel):
    id: int
    user_id: int
    asset_type: str
    market: str
    code: str
    name: str
    baseline_price: Optional[float]
    baseline_date: date
    start_date: date
    end_date: date
    created_at: datetime
    user: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=List[AssetResponse])
async def get_assets(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    asset_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取所有资产列表"""
    query = db.query(Asset)
    
    if user_id:
        query = query.filter(Asset.user_id == user_id)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    
    assets = query.offset(skip).limit(limit).all()
    
    # 构建响应数据
    result = []
    for asset in assets:
        asset_dict = {
            "id": asset.id,
            "user_id": asset.user_id,
            "asset_type": asset.asset_type,
            "market": asset.market,
            "code": asset.code,
            "name": asset.name,
            "baseline_price": asset.baseline_price,
            "baseline_date": asset.baseline_date,
            "start_date": asset.start_date,
            "end_date": asset.end_date,
            "created_at": asset.created_at,
            "user": {"id": asset.user.id, "name": asset.user.name, "avatar_url": asset.user.avatar_url} if asset.user else None
        }
        result.append(asset_dict)
    
    return result


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(asset_id: int, db: Session = Depends(get_db)):
    """获取资产详情"""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    if asset.user:
        asset.user = {"id": asset.user.id, "name": asset.user.name, "avatar_url": asset.user.avatar_url}
    
    return asset


@router.post("", response_model=AssetResponse)
async def create_asset(asset: AssetCreate, db: Session = Depends(get_db)):
    """创建新资产"""
    # 验证用户存在
    user = db.query(User).filter(User.id == asset.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查该用户是否已有资产（每个用户只能绑定一个资产）
    existing = db.query(Asset).filter(Asset.user_id == asset.user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="该用户已绑定资产，每个用户只能绑定一个资产")
    
    asset_dict = asset.dict()
    # 转换日期字符串
    for date_field in ["baseline_date", "start_date", "end_date"]:
        if asset_dict.get(date_field):
            asset_dict[date_field] = date.fromisoformat(asset_dict[date_field])
    
    db_asset = Asset(**asset_dict)
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    
    asset_dict = {
        "id": db_asset.id,
        "user_id": db_asset.user_id,
        "asset_type": db_asset.asset_type,
        "market": db_asset.market,
        "code": db_asset.code,
        "name": db_asset.name,
        "baseline_price": db_asset.baseline_price,
        "baseline_date": db_asset.baseline_date,
        "start_date": db_asset.start_date,
        "end_date": db_asset.end_date,
        "created_at": db_asset.created_at,
        "user": {"id": db_asset.user.id, "name": db_asset.user.name, "avatar_url": db_asset.user.avatar_url} if db_asset.user else None
    }
    
    return asset_dict


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: int,
    asset_update: AssetUpdate,
    db: Session = Depends(get_db)
):
    """更新资产信息"""
    db_asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not db_asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    update_data = asset_update.dict(exclude_unset=True)
    
    # 转换日期字符串
    for date_field in ["baseline_date", "start_date", "end_date"]:
        if update_data.get(date_field):
            update_data[date_field] = date.fromisoformat(update_data[date_field])
    
    # 如果更新user_id，验证新用户存在且该用户没有其他资产
    if "user_id" in update_data:
        new_user_id = update_data["user_id"]
        # 验证新用户存在
        user = db.query(User).filter(User.id == new_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 检查新用户是否已有其他资产（除了当前资产）
        existing_asset = db.query(Asset).filter(
            Asset.user_id == new_user_id,
            Asset.id != asset_id
        ).first()
        if existing_asset:
            raise HTTPException(status_code=400, detail="该用户已绑定资产，每个用户只能绑定一个资产")
    
    for key, value in update_data.items():
        setattr(db_asset, key, value)
    
    db.commit()
    db.refresh(db_asset)
    
    asset_dict = {
        "id": db_asset.id,
        "user_id": db_asset.user_id,
        "asset_type": db_asset.asset_type,
        "market": db_asset.market,
        "code": db_asset.code,
        "name": db_asset.name,
        "baseline_price": db_asset.baseline_price,
        "baseline_date": db_asset.baseline_date,
        "start_date": db_asset.start_date,
        "end_date": db_asset.end_date,
        "created_at": db_asset.created_at,
        "user": {"id": db_asset.user.id, "name": db_asset.user.name, "avatar_url": db_asset.user.avatar_url} if db_asset.user else None
    }
    
    return asset_dict


@router.delete("/{asset_id}")
async def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    """删除资产"""
    db_asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not db_asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    db.delete(db_asset)
    db.commit()
    return {"message": "资产已删除"}
