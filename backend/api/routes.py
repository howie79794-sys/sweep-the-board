"""API路由
专门存放 FastAPI 的各个接口路径（Endpoints）
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pathlib import Path
from datetime import date, datetime, timedelta
import uuid
import json
import traceback

from database.config import get_db
from database.models import User, Asset, MarketData, Ranking, PKPool, PKPoolAsset
from services.market_data import update_asset_data, update_all_assets_data, get_latest_trading_date, calculate_stability_metrics, custom_update_asset_data
from services.ranking import save_rankings, get_or_set_baseline_price
from services.storage import upload_avatar_file, delete_avatar, normalize_avatar_url
from services.asset import AssetService
from config import MAX_UPLOAD_SIZE, ALLOWED_EXTENSIONS, BASELINE_DATE
from pydantic import BaseModel, ConfigDict, Field

# 创建路由器
router = APIRouter()

# ==================== 任务追踪系统 ====================
# 在内存中维护任务状态
tasks: dict[str, dict] = {}

def create_task() -> str:
    """创建新任务并返回 task_id"""
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "id": task_id,
        "status": "processing",  # processing/success/failed
        "progress": {"completed": 0, "total": 0},
        "error_msg": None,
        "result": None,
        "created_at": datetime.now().isoformat(),
    }
    return task_id

def update_task_progress(task_id: str, completed: int, total: int):
    """更新任务进度"""
    if task_id in tasks:
        tasks[task_id]["progress"]["completed"] = completed
        tasks[task_id]["progress"]["total"] = total

def complete_task(task_id: str, result: dict):
    """标记任务为成功"""
    if task_id in tasks:
        tasks[task_id]["status"] = "success"
        tasks[task_id]["result"] = result

def fail_task(task_id: str, error_msg: str):
    """标记任务为失败"""
    if task_id in tasks:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error_msg"] = error_msg


# ==================== Pydantic 模型 ====================

class UserCreate(BaseModel):
    name: str
    avatar_url: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    name: str
    avatar_url: Optional[str]
    created_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AssetCreate(BaseModel):
    user_id: int
    asset_type: str  # stock, fund, futures, forex
    market: str
    code: str
    name: str
    baseline_date: Optional[str] = "2026-01-05"
    start_date: Optional[str] = "2026-01-05"
    end_date: Optional[str] = "2026-12-31"
    is_core: Optional[bool] = False  # 是否为核心资产


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
    is_core: Optional[bool] = None  # 是否为核心资产


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
    is_core: bool  # 是否为核心资产
    created_at: datetime
    user: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class PKPoolCreate(BaseModel):
    name: str
    description: Optional[str] = None
    asset_ids: List[int] = Field(default_factory=list, description="池内资产ID列表")
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class PKPoolUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    asset_ids: Optional[List[int]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class PKPoolResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    created_at: datetime
    asset_count: int

    model_config = ConfigDict(from_attributes=True)


class PKPoolDetailResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    created_at: datetime
    assets: List[dict]
    chart_data: List[dict]
    snapshot_data: List[dict]

    model_config = ConfigDict(from_attributes=True)


class DataUpdateRequest(BaseModel):
    """数据更新请求模型"""
    asset_ids: Optional[List[int]] = Field(
        default=None,
        description="要更新的资产ID列表，如果为null或空数组则更新所有资产"
    )
    force: bool = Field(default=False, description="是否强制更新（即使已有数据）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "asset_ids": None,
                "force": False
            }
        }


class CustomUpdateRequest(BaseModel):
    """单点数据校准请求模型"""
    asset_id: int = Field(description="资产ID")
    target_date: str = Field(description="目标日期，格式：YYYY-MM-DD")


class MarketDataResponse(BaseModel):
    id: int
    asset_id: int
    date: str
    close_price: float
    volume: Optional[float]
    turnover_rate: Optional[float]
    pe_ratio: Optional[float]
    pb_ratio: Optional[float]
    market_cap: Optional[float]
    eps_forecast: Optional[float]
    stability_score: Optional[float]
    annual_volatility: Optional[float]
    daily_returns: Optional[List[float]]
    additional_data: Optional[dict]
    created_at: str

    class Config:
        from_attributes = True


# ==================== 用户管理路由 ====================

@router.get("/users", response_model=List[UserResponse], tags=["users"])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取所有用户列表"""
    users = db.query(User).filter(User.is_active == True).offset(skip).limit(limit).all()
    # 处理旧路径头像 URL（如果出错不影响返回用户列表）
    for user in users:
        if user.avatar_url:
            try:
                user.avatar_url = normalize_avatar_url(user.avatar_url)
            except Exception as e:
                # 头像处理失败不影响用户列表返回
                print(f"[API] 处理用户 {user.id} 头像 URL 时出错: {str(e)}")
                user.avatar_url = None
    return users


@router.get("/users/{user_id}", response_model=UserResponse, tags=["users"])
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """获取用户详情"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    # 处理旧路径头像 URL
    if user.avatar_url:
        user.avatar_url = normalize_avatar_url(user.avatar_url)
    return user


@router.post("/users", response_model=UserResponse, tags=["users"])
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """创建新用户"""
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    # 处理旧路径头像 URL
    if db_user.avatar_url:
        db_user.avatar_url = normalize_avatar_url(db_user.avatar_url)
    return db_user


@router.put("/users/{user_id}", response_model=UserResponse, tags=["users"])
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db)
):
    """更新用户信息"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    # 处理旧路径头像 URL
    if db_user.avatar_url:
        db_user.avatar_url = normalize_avatar_url(db_user.avatar_url)
    return db_user


@router.delete("/users/{user_id}", tags=["users"])
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    """删除用户"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    db.delete(db_user)
    db.commit()
    return {"message": "用户已删除"}


@router.post("/users/{user_id}/avatar", tags=["users"])
async def handle_upload_avatar(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传用户头像到 Supabase Storage"""
    # 验证用户
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 验证文件大小
    file_content = await file.read()
    if len(file_content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"文件大小超过限制（{MAX_UPLOAD_SIZE / 1024 / 1024}MB）")
    
    # 验证文件类型
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式，支持格式：{', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # 生成唯一文件名
    file_name = f"{uuid.uuid4()}{file_ext}"
    
    try:
        # 删除旧头像（如果存在且是 Supabase Storage URL）
        if db_user.avatar_url:
            # 检查是否是 Supabase Storage URL
            if db_user.avatar_url.startswith("http") and "storage/v1/object/public" in db_user.avatar_url:
                await delete_avatar(db_user.avatar_url)
            # 如果是旧的本地路径，也尝试删除（兼容旧数据）
            elif db_user.avatar_url.startswith("/avatars/"):
                # 旧数据，不删除（因为可能已经不存在了）
                pass
        
        # 上传到 Supabase Storage
        public_url = await upload_avatar_file(file_content, file_name)
        
        # 更新用户头像URL（存储完整的 Supabase Storage 公网 URL）
        db_user.avatar_url = public_url
        db.commit()
        db.refresh(db_user)
        
        return {"message": "头像上传成功", "avatar_url": db_user.avatar_url}
        
    except Exception as e:
        db.rollback()
        error_msg = f"上传头像失败: {str(e)}"
        print(f"[API] {error_msg}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)


# ==================== 资产管理路由 ====================

@router.get("/assets", response_model=List[AssetResponse], tags=["assets"])
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
            "is_core": asset.is_core,
            "baseline_price": asset.baseline_price,
            "baseline_date": asset.baseline_date,
            "start_date": asset.start_date,
            "end_date": asset.end_date,
            "is_core": asset.is_core,
            "created_at": asset.created_at,
            "user": {"id": asset.user.id, "name": asset.user.name, "avatar_url": normalize_avatar_url(asset.user.avatar_url)} if asset.user else None
        }
        result.append(asset_dict)
    
    return result


@router.get("/assets/{asset_id}", response_model=AssetResponse, tags=["assets"])
async def get_asset(asset_id: int, db: Session = Depends(get_db)):
    """获取资产详情"""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    if asset.user:
        asset.user = {"id": asset.user.id, "name": asset.user.name, "avatar_url": normalize_avatar_url(asset.user.avatar_url)}
    
    return asset


@router.post("/assets", response_model=AssetResponse, tags=["assets"])
async def create_asset(asset: AssetCreate, db: Session = Depends(get_db)):
    """创建新资产"""
    # 验证用户存在
    user = db.query(User).filter(User.id == asset.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    AssetService.ensure_single_core_asset(db, asset.user_id, asset.is_core)
    
    # 校验核心资产逻辑：如果要设置 is_core=True，确保该用户没有其他核心资产
    if asset.is_core:
        existing_core = db.query(Asset).filter(
            Asset.user_id == asset.user_id,
            Asset.is_core == True
        ).first()
        if existing_core:
            raise HTTPException(status_code=400, detail="该用户已有关联的核心资产，请先取消原核心设置")
    
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
        "is_core": db_asset.is_core,
        "baseline_price": db_asset.baseline_price,
        "baseline_date": db_asset.baseline_date,
        "start_date": db_asset.start_date,
        "end_date": db_asset.end_date,
        "is_core": db_asset.is_core,
        "created_at": db_asset.created_at,
        "user": {"id": db_asset.user.id, "name": db_asset.user.name, "avatar_url": db_asset.user.avatar_url} if db_asset.user else None
    }
    
    return asset_dict


@router.put("/assets/{asset_id}", response_model=AssetResponse, tags=["assets"])
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

    target_user_id = update_data.get("user_id", db_asset.user_id)
    target_is_core = update_data.get("is_core", db_asset.is_core)
    AssetService.ensure_single_core_asset(db, target_user_id, target_is_core, asset_id=asset_id)
    
    # 转换日期字符串
    for date_field in ["baseline_date", "start_date", "end_date"]:
        if update_data.get(date_field):
            update_data[date_field] = date.fromisoformat(update_data[date_field])
    
    # 如果更新user_id，验证新用户存在
    if "user_id" in update_data:
        new_user_id = update_data["user_id"]
        # 验证新用户存在
        user = db.query(User).filter(User.id == new_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
    
    # 校验核心资产逻辑：如果要设置 is_core=True，确保该用户没有其他核心资产
    if "is_core" in update_data and update_data["is_core"] == True:
        # 获取要更新的用户ID（可能是当前的，也可能是新的）
        target_user_id = update_data.get("user_id", db_asset.user_id)
        
        # 检查该用户是否已有其他核心资产（排除当前资产）
        existing_core = db.query(Asset).filter(
            Asset.user_id == target_user_id,
            Asset.is_core == True,
            Asset.id != asset_id
        ).first()
        
        if existing_core:
            raise HTTPException(status_code=400, detail="该用户已有关联的核心资产，请先取消原核心设置")
    
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
        "is_core": db_asset.is_core,
        "baseline_price": db_asset.baseline_price,
        "baseline_date": db_asset.baseline_date,
        "start_date": db_asset.start_date,
        "end_date": db_asset.end_date,
        "is_core": db_asset.is_core,
        "created_at": db_asset.created_at,
        "user": {"id": db_asset.user.id, "name": db_asset.user.name, "avatar_url": db_asset.user.avatar_url} if db_asset.user else None
    }
    
    return asset_dict


@router.delete("/assets/{asset_id}", tags=["assets"])
async def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    """删除资产"""
    db_asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not db_asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    db.delete(db_asset)
    db.commit()
    return {"message": "资产已删除"}


# ==================== PK池管理路由 ====================

@router.get("/pk-pools", response_model=List[PKPoolResponse], tags=["pk_pools"])
async def get_pk_pools(db: Session = Depends(get_db)):
    """获取所有PK池列表"""
    pools = db.query(PKPool).order_by(PKPool.created_at.desc()).all()
    results = []
    for pool in pools:
        asset_count = db.query(func.count(PKPoolAsset.id)).filter(
            PKPoolAsset.pool_id == pool.id
        ).scalar() or 0
        results.append({
            "id": pool.id,
            "name": pool.name,
            "description": pool.description,
            "start_date": pool.start_date,
            "end_date": pool.end_date,
            "created_at": pool.created_at,
            "asset_count": asset_count,
        })
    return results


@router.post("/pk-pools", response_model=PKPoolResponse, tags=["pk_pools"])
async def create_pk_pool(pool: PKPoolCreate, db: Session = Depends(get_db)):
    """创建PK池"""
    existing = db.query(PKPool).filter(PKPool.name == pool.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="该PK池名称已存在，请更换名称")

    start_date_obj = date.fromisoformat(pool.start_date) if pool.start_date else None
    end_date_obj = date.fromisoformat(pool.end_date) if pool.end_date else None
    if start_date_obj and end_date_obj and start_date_obj > end_date_obj:
        raise HTTPException(status_code=400, detail="开始时间不能晚于结束时间")

    db_pool = PKPool(
        name=pool.name,
        description=pool.description,
        start_date=start_date_obj,
        end_date=end_date_obj,
    )
    db.add(db_pool)
    db.commit()
    db.refresh(db_pool)

    if pool.asset_ids:
        assets = db.query(Asset).filter(Asset.id.in_(pool.asset_ids)).all()
        found_ids = {asset.id for asset in assets}
        missing_ids = [asset_id for asset_id in pool.asset_ids if asset_id not in found_ids]
        if missing_ids:
            raise HTTPException(status_code=400, detail=f"资产不存在: {missing_ids}")

        for asset_id in pool.asset_ids:
            db.add(PKPoolAsset(pool_id=db_pool.id, asset_id=asset_id))
        db.commit()

    asset_count = len(pool.asset_ids)
    return {
        "id": db_pool.id,
        "name": db_pool.name,
        "description": db_pool.description,
        "start_date": db_pool.start_date,
        "end_date": db_pool.end_date,
        "created_at": db_pool.created_at,
        "asset_count": asset_count,
    }


@router.get("/pk-pools/{pool_id}", tags=["pk_pools"])
async def get_pk_pool(pool_id: int, db: Session = Depends(get_db)):
    """获取PK池详情"""
    pool = db.query(PKPool).filter(PKPool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="PK池不存在")

    assets = db.query(Asset).join(PKPoolAsset, PKPoolAsset.asset_id == Asset.id).filter(
        PKPoolAsset.pool_id == pool_id
    ).all()
    asset_list = [
        {
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
            "is_core": asset.is_core,
            "created_at": asset.created_at,
            "user": {"id": asset.user.id, "name": asset.user.name, "avatar_url": normalize_avatar_url(asset.user.avatar_url)} if asset.user else None
        }
        for asset in assets
    ]

    return {
        "id": pool.id,
        "name": pool.name,
        "description": pool.description,
        "start_date": pool.start_date,
        "end_date": pool.end_date,
        "created_at": pool.created_at,
        "assets": asset_list,
    }


@router.put("/pk-pools/{pool_id}", response_model=PKPoolResponse, tags=["pk_pools"])
async def update_pk_pool(pool_id: int, pool_update: PKPoolUpdate, db: Session = Depends(get_db)):
    """更新PK池"""
    pool = db.query(PKPool).filter(PKPool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="PK池不存在")

    update_data = pool_update.dict(exclude_unset=True)

    if "name" in update_data and update_data["name"] != pool.name:
        existing = db.query(PKPool).filter(PKPool.name == update_data["name"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="该PK池名称已存在，请更换名称")
        pool.name = update_data["name"]

    if "description" in update_data:
        pool.description = update_data["description"]

    if "start_date" in update_data:
        pool.start_date = date.fromisoformat(update_data["start_date"]) if update_data["start_date"] else None

    if "end_date" in update_data:
        pool.end_date = date.fromisoformat(update_data["end_date"]) if update_data["end_date"] else None

    if pool.start_date and pool.end_date and pool.start_date > pool.end_date:
        raise HTTPException(status_code=400, detail="开始时间不能晚于结束时间")

    if "asset_ids" in update_data and update_data["asset_ids"] is not None:
        asset_ids = update_data["asset_ids"]
        assets = db.query(Asset).filter(Asset.id.in_(asset_ids)).all() if asset_ids else []
        found_ids = {asset.id for asset in assets}
        missing_ids = [asset_id for asset_id in asset_ids if asset_id not in found_ids]
        if missing_ids:
            raise HTTPException(status_code=400, detail=f"资产不存在: {missing_ids}")

        db.query(PKPoolAsset).filter(PKPoolAsset.pool_id == pool_id).delete()
        for asset_id in asset_ids:
            db.add(PKPoolAsset(pool_id=pool_id, asset_id=asset_id))

    db.commit()
    db.refresh(pool)

    asset_count = db.query(func.count(PKPoolAsset.id)).filter(
        PKPoolAsset.pool_id == pool_id
    ).scalar() or 0

    return {
        "id": pool.id,
        "name": pool.name,
        "description": pool.description,
        "start_date": pool.start_date,
        "end_date": pool.end_date,
        "created_at": pool.created_at,
        "asset_count": asset_count,
    }


@router.delete("/pk-pools/{pool_id}", tags=["pk_pools"])
async def delete_pk_pool(pool_id: int, db: Session = Depends(get_db)):
    """删除PK池"""
    pool = db.query(PKPool).filter(PKPool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="PK池不存在")

    db.delete(pool)
    db.commit()
    return {"message": "PK池已删除"}


@router.get("/pk-pools/{pool_id}/detail", response_model=PKPoolDetailResponse, tags=["pk_pools"])
async def get_pk_pool_detail(
    pool_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取PK池详情（包含图表和指标数据）"""
    pool = db.query(PKPool).filter(PKPool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="PK池不存在")

    assets = db.query(Asset).join(PKPoolAsset, PKPoolAsset.asset_id == Asset.id).filter(
        PKPoolAsset.pool_id == pool_id
    ).all()

    baseline_date_obj = date.fromisoformat(BASELINE_DATE) if isinstance(BASELINE_DATE, str) else BASELINE_DATE
    start_date_obj = date.fromisoformat(start_date) if start_date else (pool.start_date or baseline_date_obj)
    end_date_obj = date.fromisoformat(end_date) if end_date else (pool.end_date or date.today())
    if start_date_obj > end_date_obj:
        raise HTTPException(status_code=400, detail="开始时间不能晚于结束时间")

    chart_results = []
    snapshot_results = []

    for asset in assets:
        market_data_list = db.query(MarketData).filter(
            MarketData.asset_id == asset.id,
            MarketData.date >= start_date_obj,
            MarketData.date <= end_date_obj
        ).order_by(MarketData.date.asc()).all()

        baseline_price = asset.baseline_price
        if not baseline_price:
            baseline_data = db.query(MarketData).filter(
                MarketData.asset_id == asset.id,
                MarketData.date == baseline_date_obj
            ).first()
            if baseline_data:
                baseline_price = baseline_data.close_price

        data_points = []
        for md in market_data_list:
            change_rate = None
            if baseline_price and baseline_price > 0:
                change_rate = ((md.close_price - baseline_price) / baseline_price) * 100
            data_points.append({
                "date": md.date.isoformat(),
                "close_price": md.close_price,
                "change_rate": change_rate,
                "pe_ratio": md.pe_ratio if md.pe_ratio is not None else 0.0,
                "pb_ratio": md.pb_ratio if md.pb_ratio is not None else 0.0,
                "market_cap": md.market_cap if md.market_cap is not None else 0.0,
                "eps_forecast": md.eps_forecast if md.eps_forecast is not None else 0.0,
            })

        chart_results.append({
            "asset_id": asset.id,
            "code": asset.code,
            "name": asset.name,
            "baseline_price": baseline_price,
            "baseline_date": asset.baseline_date.isoformat() if asset.baseline_date else None,
            "user": {
                "id": asset.user.id,
                "name": asset.user.name,
                "avatar_url": normalize_avatar_url(asset.user.avatar_url) if asset.user.avatar_url else None
            } if asset.user else None,
            "data": data_points
        })

        latest_trading_date = get_latest_trading_date(db, asset.id)
        latest_data = db.query(MarketData).filter(
            MarketData.asset_id == asset.id,
            MarketData.date == latest_trading_date
        ).first()

        baseline_data = db.query(MarketData).filter(
            MarketData.asset_id == asset.id,
            MarketData.date == baseline_date_obj
        ).first()

        baseline_price = baseline_data.close_price if baseline_data else asset.baseline_price
        baseline_pe_ratio = baseline_data.pe_ratio if baseline_data and baseline_data.pe_ratio is not None else None

        change_rate = None
        if latest_data and baseline_price and baseline_price > 0:
            change_rate = ((latest_data.close_price - baseline_price) / baseline_price) * 100

        yesterday_data = db.query(MarketData).filter(
            MarketData.asset_id == asset.id,
            MarketData.date < latest_trading_date
        ).order_by(MarketData.date.desc()).first()

        yesterday_close_price = yesterday_data.close_price if yesterday_data else None
        daily_change_rate = None
        if latest_data and yesterday_close_price and yesterday_close_price > 0:
            daily_change_rate = ((latest_data.close_price - yesterday_close_price) / yesterday_close_price) * 100

        pe_ratio = latest_data.pe_ratio if latest_data and latest_data.pe_ratio is not None else None
        pb_ratio = latest_data.pb_ratio if latest_data and latest_data.pb_ratio is not None else None
        market_cap = latest_data.market_cap if latest_data and latest_data.market_cap is not None else None
        eps_forecast = latest_data.eps_forecast if latest_data and latest_data.eps_forecast is not None else None

        stability_metrics = calculate_stability_metrics(asset.id, db)

        snapshot_results.append({
            "asset_id": asset.id,
            "code": asset.code,
            "name": asset.name,
            "user": {
                "id": asset.user.id,
                "name": asset.user.name,
                "avatar_url": normalize_avatar_url(asset.user.avatar_url) if asset.user.avatar_url else None
            } if asset.user else None,
            "baseline_price": baseline_price,
            "baseline_date": baseline_date_obj.isoformat(),
            "latest_date": latest_trading_date.isoformat(),
            "latest_close_price": latest_data.close_price if latest_data else None,
            "yesterday_close_price": yesterday_close_price,
            "daily_change_rate": daily_change_rate,
            "latest_market_cap": market_cap,
            "eps_forecast": eps_forecast,
            "change_rate": change_rate,
            "pe_ratio": pe_ratio,
            "pb_ratio": pb_ratio,
            "baseline_pe_ratio": baseline_pe_ratio,
            "stability_score": stability_metrics["stability_score"],
            "annual_volatility": stability_metrics["annual_volatility"],
            "daily_returns": stability_metrics["daily_returns"],
        })

    asset_list = [
        {
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
            "is_core": asset.is_core,
            "created_at": asset.created_at,
            "user": {"id": asset.user.id, "name": asset.user.name, "avatar_url": normalize_avatar_url(asset.user.avatar_url)} if asset.user else None
        }
        for asset in assets
    ]

    return {
        "id": pool.id,
        "name": pool.name,
        "description": pool.description,
        "start_date": pool.start_date,
        "end_date": pool.end_date,
        "created_at": pool.created_at,
        "assets": asset_list,
        "chart_data": chart_results,
        "snapshot_data": snapshot_results,
    }


# ==================== 数据管理路由 ====================

@router.get("/data/assets/{asset_id}", tags=["data"])
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
            "pb_ratio": data.pb_ratio,
            "market_cap": data.market_cap,
            "eps_forecast": data.eps_forecast,
            "additional_data": None,
            "created_at": data.created_at.isoformat() if data.created_at else None
        }
        if data.additional_data:
            try:
                data_dict["additional_data"] = json.loads(data.additional_data)
            except:
                pass
        result.append(data_dict)
    
    return result


@router.get("/data/assets/{asset_id}/latest", tags=["data"])
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
        "pb_ratio": latest.pb_ratio,
        "market_cap": latest.market_cap,
        "eps_forecast": latest.eps_forecast,
        "additional_data": None,
        "created_at": latest.created_at.isoformat() if latest.created_at else None
    }
    
    if latest.additional_data:
        try:
            result["additional_data"] = json.loads(latest.additional_data)
        except:
            pass
    
    return result


@router.get("/data/assets/{asset_id}/baseline", tags=["data"])
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


def run_update_task(task_id: str, asset_ids: Optional[List[int]], force: bool):
    """后台执行数据更新任务"""
    # 创建新的数据库会话（BackgroundTasks 中不能使用 Depends）
    db = next(get_db())
    try:
        print(f"[API] [任务 {task_id}] ========== 开始执行数据更新任务 ==========")
        
        # 如果 asset_ids 不为 None 且不为空列表，则更新指定资产
        if asset_ids and len(asset_ids) > 0:
            print(f"[API] [任务 {task_id}] 更新指定资产: {asset_ids}")
            total = len(asset_ids)
            update_task_progress(task_id, 0, total)
            
            results = []
            for idx, asset_id in enumerate(asset_ids, 1):
                print(f"[API] [任务 {task_id}] 处理资产 ID: {asset_id} ({idx}/{total})")
                try:
                    result = update_asset_data(asset_id, db, force)
                    results.append({
                        "asset_id": asset_id,
                        **result
                    })
                except Exception as e:
                    # 单个资产失败不影响整体
                    error_msg = f"处理资产 {asset_id} 时发生异常: {type(e).__name__}: {str(e)}"
                    print(f"[API] [任务 {task_id}] ✗ {error_msg}")
                    traceback.print_exc()
                    results.append({
                        "asset_id": asset_id,
                        "success": False,
                        "message": error_msg,
                        "stored_count": 0,
                        "new_data_count": 0,
                        "filled_metrics_count": 0
                    })
                
                update_task_progress(task_id, idx, total)
            
            print(f"[API] [任务 {task_id}] 开始计算排名...")
            # 计算排名
            try:
                today = date.today()
                save_rankings(today, db)
                print(f"[API] [任务 {task_id}] 排名计算完成")
            except Exception as e:
                print(f"[API] [任务 {task_id}] 警告: 计算排名时发生错误: {type(e).__name__}: {str(e)}")
                traceback.print_exc()
            
            result = {
                "message": "数据更新完成",
                "results": results
            }
            complete_task(task_id, result)
            print(f"[API] [任务 {task_id}] ========== 数据更新任务完成 ==========")
        else:
            print(f"[API] [任务 {task_id}] 更新所有资产")
            # 获取所有资产数量
            assets = db.query(Asset).all()
            total = len(assets)
            update_task_progress(task_id, 0, total)
            
            # 更新所有资产（外层包裹异常捕获，确保单个资产失败不会导致整个接口崩溃）
            try:
                # 修改 update_all_assets_data 以支持进度回调
                results = {
                    "total": total,
                    "success": 0,
                    "failed": 0,
                    "details": []
                }
                
                for idx, asset in enumerate(assets, 1):
                    print(f"[API] [任务 {task_id}] -------- 处理资产 {idx}/{total}: {asset.name} (ID: {asset.id}) --------")
                    try:
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
                    except Exception as e:
                        # 单个资产失败不应该导致整个批量更新崩溃
                        results["failed"] += 1
                        error_msg = f"处理资产时发生异常: {type(e).__name__}: {str(e)}"
                        print(f"[API] [任务 {task_id}] ✗ 资产 {asset.name} 处理异常: {error_msg}")
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
                    
                    update_task_progress(task_id, idx, total)
                
            except Exception as e:
                print(f"[API] [任务 {task_id}] 错误: 批量更新资产数据时发生异常: {type(e).__name__}: {str(e)}")
                traceback.print_exc()
                # 返回部分结果，而不是抛出异常
                results = {
                    "total": total,
                    "success": 0,
                    "failed": 0,
                    "details": [],
                    "error": f"批量更新过程中发生错误: {str(e)}"
                }
            
            print(f"[API] [任务 {task_id}] 开始计算排名...")
            # 计算排名（也包裹异常捕获）
            try:
                today = date.today()
                save_rankings(today, db)
                print(f"[API] [任务 {task_id}] 排名计算完成")
            except Exception as e:
                print(f"[API] [任务 {task_id}] 警告: 计算排名时发生错误: {type(e).__name__}: {str(e)}")
                traceback.print_exc()
                # 排名计算失败不影响数据更新结果
            
            result = {
                "message": "所有资产数据更新完成",
                **results
            }
            complete_task(task_id, result)
            print(f"[API] [任务 {task_id}] ========== 数据更新任务完成 ==========")
    except Exception as e:
        error_msg = f"数据更新任务执行失败: {type(e).__name__}: {str(e)}"
        print(f"[API] [任务 {task_id}] 错误: {error_msg}")
        traceback.print_exc()
        fail_task(task_id, error_msg)
    finally:
        # 确保数据库会话关闭
        db.close()


@router.post("/data/update", tags=["data"])
async def trigger_update(
    request: DataUpdateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """触发数据更新（支持全部或指定资产）- 异步模式"""
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
    
    # 处理 asset_ids：None、空列表或有效列表
    asset_ids = request.asset_ids if request.asset_ids else None
    force = request.force
    
    print(f"[API] 解析后的参数: asset_ids={asset_ids} (类型: {type(asset_ids)}), force={force}")
    
    # 创建任务
    task_id = create_task()
    print(f"[API] 创建任务: {task_id}")
    
    # 启动后台任务（不传递 db，在任务内部创建）
    background_tasks.add_task(run_update_task, task_id, asset_ids, force)
    
    # 立即返回 task_id
    return {
        "task_id": task_id,
        "message": "数据更新任务已启动",
        "status": "processing"
    }


@router.get("/data/task/{task_id}", tags=["data"])
async def get_task_status(task_id: str):
    """查询任务状态"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks[task_id]
    return {
        "id": task["id"],
        "status": task["status"],
        "progress": task["progress"],
        "error_msg": task["error_msg"],
        "result": task["result"],
        "created_at": task["created_at"],
    }


@router.post("/data/custom-update", tags=["data"])
async def custom_update_data(
    request: CustomUpdateRequest,
    db: Session = Depends(get_db)
):
    """单点数据校准：强制覆盖指定日期的数据"""
    print(f"[API] ========== 收到单点数据校准请求 ==========")
    print(f"[API] asset_id={request.asset_id}, target_date={request.target_date}")
    
    # 验证日期格式
    try:
        # 确保日期格式为 YYYY-MM-DD
        target_date = request.target_date.strip()
        # 尝试解析日期以验证格式
        date.fromisoformat(target_date)
    except ValueError as e:
        error_msg = f"日期格式错误: {request.target_date}，必须是 YYYY-MM-DD 格式"
        print(f"[API] ✗ {error_msg}")
        raise HTTPException(status_code=422, detail=error_msg)
    
    try:
        result = custom_update_asset_data(
            asset_id=request.asset_id,
            target_date=target_date,
            db=db
        )
        
        if result["success"]:
            print(f"[API] ========== 单点数据校准成功 ==========")
            return {
                "success": True,
                "message": result["message"],
                "data": result["data"]
            }
        else:
            print(f"[API] ========== 单点数据校准失败 ==========")
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"单点数据校准失败: {type(e).__name__}: {str(e)}"
        print(f"[API] ✗ {error_msg}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/data/charts/all", tags=["data"])
async def get_all_assets_chart_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取所有资产的图表数据（收益率和收盘价），用于首页图表展示"""
    # 默认使用基准日期作为起始日期
    baseline_date_obj = date.fromisoformat(BASELINE_DATE) if isinstance(BASELINE_DATE, str) else BASELINE_DATE
    start_date_obj = date.fromisoformat(start_date) if start_date else baseline_date_obj
    end_date_obj = date.fromisoformat(end_date) if end_date else date.today()
    
    # 获取所有活跃的核心资产
    assets = db.query(Asset).join(User).filter(User.is_active == True, Asset.is_core == True).all()
    
    result = []
    for asset in assets:
        # 获取该资产在日期范围内的市场数据
        market_data_query = db.query(MarketData).filter(
            MarketData.asset_id == asset.id,
            MarketData.date >= start_date_obj,
            MarketData.date <= end_date_obj
        ).order_by(MarketData.date.asc())
        
        market_data_list = market_data_query.all()
        
        # 获取基准价格
        baseline_price = asset.baseline_price
        if not baseline_price:
            # 如果没有基准价格，尝试从基准日期的市场数据获取
            baseline_data = db.query(MarketData).filter(
                MarketData.asset_id == asset.id,
                MarketData.date == baseline_date_obj
            ).first()
            if baseline_data:
                baseline_price = baseline_data.close_price
        
        # 构建数据点，并填充周末数据（使用前一个交易日的值）
        data_points = []
        last_valid_data = None  # 用于存储最近一个有效交易日的数据
        
        # 生成日期范围内的所有日期（包括周末）
        current_date = start_date_obj
        while current_date <= end_date_obj:
            # 查找该日期是否有市场数据
            md = next((m for m in market_data_list if m.date == current_date), None)
            
            if md:
                # 有数据，使用实际数据
                last_valid_data = {
                    "close_price": md.close_price,
                    "pe_ratio": md.pe_ratio if md.pe_ratio is not None else 0.0,
                    "pb_ratio": md.pb_ratio if md.pb_ratio is not None else 0.0,
                    "market_cap": md.market_cap if md.market_cap is not None else 0.0,
                    "eps_forecast": md.eps_forecast if md.eps_forecast is not None else 0.0,
                }
            elif last_valid_data:
                # 无数据但之前有有效数据（可能是周末），使用前一个交易日的值
                # 直接构建数据点，使用前一个交易日的值
                data_point = {
                    "date": current_date.isoformat(),
                    "close_price": last_valid_data["close_price"],
                    "pe_ratio": last_valid_data["pe_ratio"],
                    "pb_ratio": last_valid_data["pb_ratio"],
                    "market_cap": last_valid_data["market_cap"],
                    "eps_forecast": last_valid_data["eps_forecast"],
                }
                
                # 计算收益率（相对于基准价格）
                if baseline_price and baseline_price > 0:
                    change_rate = ((last_valid_data["close_price"] - baseline_price) / baseline_price) * 100
                    data_point["change_rate"] = change_rate
                else:
                    data_point["change_rate"] = None
                
                data_points.append(data_point)
                current_date += timedelta(days=1)
                continue
            else:
                # 无数据且之前也没有有效数据，跳过该日期
                current_date += timedelta(days=1)
                continue
            
            # 构建数据点（有实际数据的情况）
            data_point = {
                "date": md.date.isoformat(),
                "close_price": md.close_price,
            }
            
            # 计算收益率（相对于基准价格）
            if baseline_price and baseline_price > 0:
                change_rate = ((md.close_price - baseline_price) / baseline_price) * 100
                data_point["change_rate"] = change_rate
            else:
                data_point["change_rate"] = None
            
            # 添加所有财务指标数据 - 确保返回数字 0 而不是 null，以便前端 Tooltip 能够正常捕获数值
            data_point["pe_ratio"] = md.pe_ratio if md.pe_ratio is not None else 0.0
            data_point["pb_ratio"] = md.pb_ratio if md.pb_ratio is not None else 0.0
            data_point["market_cap"] = md.market_cap if md.market_cap is not None else 0.0
            data_point["eps_forecast"] = md.eps_forecast if md.eps_forecast is not None else 0.0
            
            # 调试：打印第一条数据的财务指标
            if len(data_points) == 0:
                print(f"[API] 图表数据点财务指标 (资产: {asset.code}): PE={md.pe_ratio}, PB={md.pb_ratio}, 市值={md.market_cap}, EPS={md.eps_forecast}")
            
            data_points.append(data_point)
            
            # 移动到下一天
            current_date += timedelta(days=1)
        
        if data_points:  # 只有当有数据点时才添加到结果中
            result.append({
                "asset_id": asset.id,
                "code": asset.code,
                "name": asset.name,
                "baseline_price": baseline_price,
                "baseline_date": asset.baseline_date.isoformat() if asset.baseline_date else None,
                "user": {
                    "id": asset.user.id,
                    "name": asset.user.name,
                    "avatar_url": normalize_avatar_url(asset.user.avatar_url) if asset.user.avatar_url else None
                },
                "data": data_points
            })
    
    return result


@router.get("/data/markets/types", tags=["data"])
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


@router.get("/data/snapshot", tags=["data"])
async def get_snapshot_data(db: Session = Depends(get_db)):
    """
    获取所有资产在"北京时间上个交易日"的最新快照数据
    
    返回每个资产的最新一条数据，包含：
    - 关联用户信息
    - 股票代码/名称
    - 基准价格（2026/01/05的收盘价）
    - 最新收盘价（上个交易日的成交价）
    - 最新总市值（亿元）
    - EPS预测
    - 累计收益（相对于基准价格）
    """
    # 获取最新交易日
    latest_trading_date = get_latest_trading_date(db)
    
    # 获取所有活跃的核心资产
    assets = db.query(Asset).join(User).filter(User.is_active == True, Asset.is_core == True).all()
    
    baseline_date_obj = date.fromisoformat(BASELINE_DATE) if isinstance(BASELINE_DATE, str) else BASELINE_DATE
    
    result = []
    for asset in assets:
        # 获取该资产在最新交易日的数据
        latest_data = db.query(MarketData).filter(
            MarketData.asset_id == asset.id,
            MarketData.date == latest_trading_date
        ).first()
        
        # 获取基准价格（2026/01/05的收盘价）
        baseline_data = db.query(MarketData).filter(
            MarketData.asset_id == asset.id,
            MarketData.date == baseline_date_obj
        ).first()
        
        baseline_price = baseline_data.close_price if baseline_data else asset.baseline_price
        baseline_pe_ratio = baseline_data.pe_ratio if baseline_data and baseline_data.pe_ratio is not None else None
        
        # 计算累计收益
        change_rate = None
        if latest_data and baseline_price and baseline_price > 0:
            change_rate = ((latest_data.close_price - baseline_price) / baseline_price) * 100
        
        # 获取昨天的收盘价（用于计算涨跌幅）
        # 查找最新交易日之前最近的一个交易日的数据
        yesterday_data = db.query(MarketData).filter(
            MarketData.asset_id == asset.id,
            MarketData.date < latest_trading_date
        ).order_by(MarketData.date.desc()).first()
        
        yesterday_close_price = yesterday_data.close_price if yesterday_data else None
        
        # 计算今天对比昨天的涨跌幅
        daily_change_rate = None
        if latest_data and yesterday_close_price and yesterday_close_price > 0:
            daily_change_rate = ((latest_data.close_price - yesterday_close_price) / yesterday_close_price) * 100
        
        # 显式获取财务指标，确保字段存在
        pe_ratio = latest_data.pe_ratio if latest_data and latest_data.pe_ratio is not None else None
        pb_ratio = latest_data.pb_ratio if latest_data and latest_data.pb_ratio is not None else None
        market_cap = latest_data.market_cap if latest_data and latest_data.market_cap is not None else None
        eps_forecast = latest_data.eps_forecast if latest_data and latest_data.eps_forecast is not None else None
        
        # 调试日志
        if latest_data:
            print(f"[API] Snapshot财务指标 (资产: {asset.code}): PE={pe_ratio}, PB={pb_ratio}, 市值={market_cap}, EPS={eps_forecast}")
        
        # 计算稳健度指标
        stability_metrics = calculate_stability_metrics(asset.id, db)
        print(f"[API] Snapshot稳健度指标 (资产: {asset.code}): 稳健性评分={stability_metrics['stability_score']}, 年化波动率={stability_metrics['annual_volatility']}%, 收益率数据数量={len(stability_metrics['daily_returns'])}")
        
        result.append({
            "asset_id": asset.id,
            "code": asset.code,
            "name": asset.name,
            "user": {
                "id": asset.user.id,
                "name": asset.user.name,
                "avatar_url": normalize_avatar_url(asset.user.avatar_url) if asset.user.avatar_url else None
            },
            "baseline_price": baseline_price,
            "baseline_date": baseline_date_obj.isoformat(),
            "latest_date": latest_trading_date.isoformat(),
            "latest_close_price": latest_data.close_price if latest_data else None,
            "yesterday_close_price": yesterday_close_price,
            "daily_change_rate": daily_change_rate,
            "latest_market_cap": market_cap,
            "eps_forecast": eps_forecast,
            "change_rate": change_rate,
            "pe_ratio": pe_ratio,
            "pb_ratio": pb_ratio,
            "baseline_pe_ratio": baseline_pe_ratio,
            "stability_score": stability_metrics["stability_score"],
            "annual_volatility": stability_metrics["annual_volatility"],
            "daily_returns": stability_metrics["daily_returns"],
        })
    
    return result


# ==================== 排名路由 ====================

@router.get("/ranking", tags=["ranking"])
async def get_rankings(
    ranking_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取当前排名（支持按资产/用户排名，包含涨跌幅，即使缺少基准价也返回）"""
    # 如果没有指定日期，使用最新排名日期，如果没有排名则使用今天
    if ranking_date:
        target_date = date.fromisoformat(ranking_date)
    else:
        latest_ranking = db.query(func.max(Ranking.date)).scalar()
        if not latest_ranking:
            # 如果没有排名数据，返回所有资产和用户的实时数据
            target_date = date.today()
        else:
            target_date = latest_ranking
    
    # 获取资产排名（包含有排名和没有排名的），只返回核心资产
    asset_rankings_query = db.query(Ranking).join(Asset).filter(
        Ranking.date == target_date,
        Ranking.rank_type == "asset_rank",
        Asset.is_core == True
    )
    
    # 先按有排名的排序，然后是没有排名的
    asset_rankings = asset_rankings_query.order_by(
        Ranking.asset_rank.asc().nullslast()
    ).all()
    
    # 获取用户排名（包含有排名和没有排名的），只返回核心资产
    user_rankings_query = db.query(Ranking).join(Asset).filter(
        Ranking.date == target_date,
        Ranking.rank_type == "user_rank",
        Asset.is_core == True
    )
    
    # 去重，每个用户只返回一条（取第一个）
    user_rankings_all = user_rankings_query.order_by(
        Ranking.user_rank.asc().nullslast()
    ).all()
    
    # 去重处理：每个用户只保留一条记录
    seen_users = set()
    user_rankings = []
    for ranking in user_rankings_all:
        if ranking.user_id not in seen_users:
            user_rankings.append(ranking)
            seen_users.add(ranking.user_id)
    
    # 加载关联数据，并获取当前价格
    asset_results = []
    for ranking in asset_rankings:
        # 获取最新市场数据（用于显示当前价格）
        latest_market_data = db.query(MarketData).filter(
            MarketData.asset_id == ranking.asset_id
        ).order_by(MarketData.date.desc()).first()
        
        current_price = latest_market_data.close_price if latest_market_data else None
        
        asset_results.append({
            "id": ranking.id,
            "date": ranking.date.isoformat(),
            "asset_id": ranking.asset_id,
            "user_id": ranking.user_id,
            "asset_rank": ranking.asset_rank,
            "user_rank": ranking.user_rank,
            "change_rate": ranking.change_rate,
            "current_price": current_price,
            "rank_type": ranking.rank_type,
            "created_at": ranking.created_at.isoformat() if ranking.created_at else None,
            "asset": {
                "id": ranking.asset.id,
                "user_id": ranking.asset.user_id,
                "code": ranking.asset.code,
                "name": ranking.asset.name,
                "asset_type": ranking.asset.asset_type,
                "market": ranking.asset.market,
                "baseline_price": ranking.asset.baseline_price,
                "baseline_date": ranking.asset.baseline_date.isoformat() if ranking.asset.baseline_date else None,
                "start_date": ranking.asset.start_date.isoformat() if ranking.asset.start_date else None,
                "end_date": ranking.asset.end_date.isoformat() if ranking.asset.end_date else None,
                "created_at": ranking.asset.created_at.isoformat() if ranking.asset.created_at else None,
            },
            "user": {
                "id": ranking.user.id,
                "name": ranking.user.name,
                "avatar_url": normalize_avatar_url(ranking.user.avatar_url),
                "created_at": ranking.user.created_at.isoformat() if ranking.user.created_at else None,
                "is_active": ranking.user.is_active,
            }
        })
    
    user_results = []
    for ranking in user_rankings:
        # 获取最新市场数据（用于显示当前价格）
        latest_market_data = db.query(MarketData).filter(
            MarketData.asset_id == ranking.asset_id
        ).order_by(MarketData.date.desc()).first()
        
        current_price = latest_market_data.close_price if latest_market_data else None
        
        user_results.append({
            "id": ranking.id,
            "date": ranking.date.isoformat(),
            "asset_id": ranking.asset_id,
            "user_id": ranking.user_id,
            "asset_rank": ranking.asset_rank,
            "user_rank": ranking.user_rank,
            "change_rate": ranking.change_rate,
            "current_price": current_price,
            "rank_type": ranking.rank_type,
            "created_at": ranking.created_at.isoformat() if ranking.created_at else None,
            "user": {
                "id": ranking.user.id,
                "name": ranking.user.name,
                "avatar_url": normalize_avatar_url(ranking.user.avatar_url),
                "created_at": ranking.user.created_at.isoformat() if ranking.user.created_at else None,
                "is_active": ranking.user.is_active,
            },
            "asset": {
                "id": ranking.asset.id,
                "user_id": ranking.asset.user_id,
                "code": ranking.asset.code,
                "name": ranking.asset.name,
                "asset_type": ranking.asset.asset_type,
                "market": ranking.asset.market,
                "baseline_price": ranking.asset.baseline_price,
                "baseline_date": ranking.asset.baseline_date.isoformat() if ranking.asset.baseline_date else None,
                "start_date": ranking.asset.start_date.isoformat() if ranking.asset.start_date else None,
                "end_date": ranking.asset.end_date.isoformat() if ranking.asset.end_date else None,
                "created_at": ranking.asset.created_at.isoformat() if ranking.asset.created_at else None,
            }
        })
    
    return {
        "asset_rankings": asset_results,
        "user_rankings": user_results,
        "date": target_date.isoformat()
    }


@router.get("/ranking/assets", tags=["ranking"])
async def get_asset_rankings(
    ranking_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取资产排名（按涨跌幅排序）"""
    # 实现逻辑类似上面的get_rankings，只返回资产排名
    result = await get_rankings(ranking_date, db)
    return result["asset_rankings"]


@router.get("/ranking/users", tags=["ranking"])
async def get_user_rankings(
    ranking_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取用户排名（按用户所有资产的涨跌幅表现排序）"""
    # 实现逻辑类似上面的get_rankings，只返回用户排名
    result = await get_rankings(ranking_date, db)
    return result["user_rankings"]


@router.get("/ranking/history", tags=["ranking"])
async def get_ranking_history(
    asset_id: Optional[int] = None,
    user_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取排名历史"""
    query = db.query(Ranking)
    
    if asset_id:
        query = query.filter(Ranking.asset_id == asset_id)
    if user_id:
        query = query.filter(Ranking.user_id == user_id)
    
    rankings = query.order_by(Ranking.date.desc()).limit(limit).all()
    
    results = []
    for ranking in rankings:
        results.append({
            "id": ranking.id,
            "date": ranking.date.isoformat(),
            "asset_id": ranking.asset_id,
            "user_id": ranking.user_id,
            "asset_rank": ranking.asset_rank,
            "user_rank": ranking.user_rank,
            "change_rate": ranking.change_rate,
            "rank_type": ranking.rank_type
        })
    
    return results


@router.get("/ranking/users/{user_id}", tags=["ranking"])
async def get_user_ranking_history(
    user_id: int,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取用户的排名历史"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    rankings = db.query(Ranking).filter(
        Ranking.user_id == user_id
    ).order_by(Ranking.date.desc()).limit(limit).all()
    
    results = []
    for ranking in rankings:
        results.append({
            "id": ranking.id,
            "date": ranking.date.isoformat(),
            "asset_id": ranking.asset_id,
            "asset_rank": ranking.asset_rank,
            "user_rank": ranking.user_rank,
            "change_rate": ranking.change_rate,
            "rank_type": ranking.rank_type
        })
    
    return results
