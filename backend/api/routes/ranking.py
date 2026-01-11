"""排名路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
from sqlalchemy import func

from database.base import get_db
from models.asset import Asset
from models.ranking import Ranking
from models.user import User
from models.market_data import MarketData

router = APIRouter()


@router.get("")
async def get_rankings(
    ranking_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取当前排名（支持按资产/用户排名，包含涨跌幅）"""
    # 如果没有指定日期，使用最新排名日期
    if ranking_date:
        target_date = date.fromisoformat(ranking_date)
    else:
        latest_ranking = db.query(func.max(Ranking.date)).scalar()
        if not latest_ranking:
            return {"asset_rankings": [], "user_rankings": [], "date": None}
        target_date = latest_ranking
    
    # 获取资产排名
    asset_rankings = db.query(Ranking).filter(
        Ranking.date == target_date,
        Ranking.rank_type == "asset_rank"
    ).order_by(Ranking.asset_rank.asc()).all()
    
    # 获取用户排名
    user_rankings = db.query(Ranking).filter(
        Ranking.date == target_date,
        Ranking.rank_type == "user_rank"
    ).order_by(Ranking.user_rank.asc()).all()
    
    # 加载关联数据
    asset_results = []
    for ranking in asset_rankings:
        asset_results.append({
            "id": ranking.id,
            "date": ranking.date.isoformat(),
            "asset_id": ranking.asset_id,
            "user_id": ranking.user_id,
            "asset_rank": ranking.asset_rank,
            "user_rank": ranking.user_rank,
            "change_rate": ranking.change_rate,
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
                "avatar_url": ranking.user.avatar_url,
                "created_at": ranking.user.created_at.isoformat() if ranking.user.created_at else None,
                "is_active": ranking.user.is_active,
            }
        })
    
    user_results = []
    for ranking in user_rankings:
        user_results.append({
            "id": ranking.id,
            "date": ranking.date.isoformat(),
            "asset_id": ranking.asset_id,
            "user_id": ranking.user_id,
            "asset_rank": ranking.asset_rank,
            "user_rank": ranking.user_rank,
            "change_rate": ranking.change_rate,
            "rank_type": ranking.rank_type,
            "created_at": ranking.created_at.isoformat() if ranking.created_at else None,
            "user": {
                "id": ranking.user.id,
                "name": ranking.user.name,
                "avatar_url": ranking.user.avatar_url,
                "created_at": ranking.user.created_at.isoformat() if ranking.user.created_at else None,
                "is_active": ranking.user.is_active,
            }
        })
    
    return {
        "asset_rankings": asset_results,
        "user_rankings": user_results,
        "date": target_date.isoformat()
    }


@router.get("/assets")
async def get_asset_rankings(
    ranking_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取资产排名（按涨跌幅排序）"""
    # 实现逻辑类似上面的get_rankings，只返回资产排名
    result = await get_rankings(ranking_date, db)
    return result["asset_rankings"]


@router.get("/users")
async def get_user_rankings(
    ranking_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取用户排名（按用户所有资产的涨跌幅表现排序）"""
    # 实现逻辑类似上面的get_rankings，只返回用户排名
    result = await get_rankings(ranking_date, db)
    return result["user_rankings"]


@router.get("/history")
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


@router.get("/users/{user_id}")
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
