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
    """获取当前排名（支持按资产/用户排名，包含涨跌幅，即使缺少基准价也返回）"""
    from datetime import date as date_type
    
    # 如果没有指定日期，使用最新排名日期，如果没有排名则使用今天
    if ranking_date:
        target_date = date_type.fromisoformat(ranking_date)
    else:
        latest_ranking = db.query(func.max(Ranking.date)).scalar()
        if not latest_ranking:
            # 如果没有排名数据，返回所有资产和用户的实时数据
            target_date = date_type.today()
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
