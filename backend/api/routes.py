"""API路由
专门存放 FastAPI 的各个接口路径（Endpoints）
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pathlib import Path
from datetime import date, datetime
import uuid
import json
import traceback

from database.config import get_db
from database.models import User, Asset, MarketData, Ranking
from services.market_data import update_asset_data, update_all_assets_data, get_latest_trading_date
from services.ranking import save_rankings, get_or_set_baseline_price
from services.storage import upload_avatar_file, delete_avatar, normalize_avatar_url
from config import MAX_UPLOAD_SIZE, ALLOWED_EXTENSIONS, BASELINE_DATE
from pydantic import BaseModel, ConfigDict, Field

# 创建路由器
router = APIRouter()


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
            "baseline_price": asset.baseline_price,
            "baseline_date": asset.baseline_date,
            "start_date": asset.start_date,
            "end_date": asset.end_date,
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


@router.delete("/assets/{asset_id}", tags=["assets"])
async def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    """删除资产"""
    db_asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not db_asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    db.delete(db_asset)
    db.commit()
    return {"message": "资产已删除"}


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


@router.post("/data/update", tags=["data"])
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
                traceback.print_exc()
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
                traceback.print_exc()
                # 排名计算失败不影响数据更新结果
            
            response = {
                "message": "所有资产数据更新完成",
                **result
            }
            print(f"[API] ========== 数据更新请求完成 ==========")
            return response
    except Exception as e:
        print(f"[API] 错误: 数据更新请求处理失败: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"数据更新失败: {str(e)}")


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
    
    # 获取所有活跃资产
    assets = db.query(Asset).join(User).filter(User.is_active == True).all()
    
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
        
        # 构建数据点
        data_points = []
        for md in market_data_list:
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
            
            # 添加所有财务指标数据 - 显式赋值，确保字段存在
            data_point["pe_ratio"] = md.pe_ratio if md.pe_ratio is not None else None
            data_point["pb_ratio"] = md.pb_ratio if md.pb_ratio is not None else None
            data_point["market_cap"] = md.market_cap if md.market_cap is not None else None
            data_point["eps_forecast"] = md.eps_forecast if md.eps_forecast is not None else None
            
            # 调试：打印第一条数据的财务指标
            if len(data_points) == 0:
                print(f"[API] 图表数据点财务指标 (资产: {asset.code}): PE={md.pe_ratio}, PB={md.pb_ratio}, 市值={md.market_cap}, EPS={md.eps_forecast}")
            
            data_points.append(data_point)
        
        if data_points:  # 只有当有数据点时才添加到结果中
            result.append({
                "asset_id": asset.id,
                "code": asset.code,
                "name": asset.name,
                "baseline_price": baseline_price,
                "baseline_date": asset.baseline_date.isoformat() if asset.baseline_date else None,
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
    
    # 获取所有活跃资产
    assets = db.query(Asset).join(User).filter(User.is_active == True).all()
    
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
        
        # 计算累计收益
        change_rate = None
        if latest_data and baseline_price and baseline_price > 0:
            change_rate = ((latest_data.close_price - baseline_price) / baseline_price) * 100
        
        # 显式获取财务指标，确保字段存在
        pe_ratio = latest_data.pe_ratio if latest_data and latest_data.pe_ratio is not None else None
        pb_ratio = latest_data.pb_ratio if latest_data and latest_data.pb_ratio is not None else None
        market_cap = latest_data.market_cap if latest_data and latest_data.market_cap is not None else None
        eps_forecast = latest_data.eps_forecast if latest_data and latest_data.eps_forecast is not None else None
        
        # 调试日志
        if latest_data:
            print(f"[API] Snapshot财务指标 (资产: {asset.code}): PE={pe_ratio}, PB={pb_ratio}, 市值={market_cap}, EPS={eps_forecast}")
        
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
            "latest_market_cap": market_cap,
            "eps_forecast": eps_forecast,
            "change_rate": change_rate,
            "pe_ratio": pe_ratio,
            "pb_ratio": pb_ratio,
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
    
    # 获取资产排名（包含有排名和没有排名的）
    asset_rankings_query = db.query(Ranking).filter(
        Ranking.date == target_date,
        Ranking.rank_type == "asset_rank"
    )
    
    # 先按有排名的排序，然后是没有排名的
    asset_rankings = asset_rankings_query.order_by(
        Ranking.asset_rank.asc().nullslast()
    ).all()
    
    # 获取用户排名（包含有排名和没有排名的）
    user_rankings_query = db.query(Ranking).filter(
        Ranking.date == target_date,
        Ranking.rank_type == "user_rank"
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
