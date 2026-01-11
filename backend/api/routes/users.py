"""用户管理路由"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path
from datetime import datetime
import shutil
import uuid

from database.base import get_db
from models.user import User
from config import UPLOAD_DIR, MAX_UPLOAD_SIZE, ALLOWED_EXTENSIONS
from pydantic import BaseModel, ConfigDict

router = APIRouter()


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


@router.get("", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取所有用户列表"""
    users = db.query(User).filter(User.is_active == True).offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """获取用户详情"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.post("", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """创建新用户"""
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.put("/{user_id}", response_model=UserResponse)
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
    return db_user


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    """删除用户"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    db.delete(db_user)
    db.commit()
    return {"message": "用户已删除"}


@router.post("/{user_id}/avatar")
async def upload_avatar(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传用户头像"""
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
    file_path = UPLOAD_DIR / file_name
    
    # 保存文件
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # 删除旧头像（如果存在）
    if db_user.avatar_url:
        old_file_path = UPLOAD_DIR / Path(db_user.avatar_url).name
        if old_file_path.exists():
            old_file_path.unlink()
    
    # 更新用户头像URL
    db_user.avatar_url = f"/avatars/{file_name}"
    db.commit()
    db.refresh(db_user)
    
    return {"message": "头像上传成功", "avatar_url": db_user.avatar_url}
