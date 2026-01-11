"""排名计算服务"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import date
from typing import List, Dict, Optional

from models.asset import Asset
from models.market_data import MarketData
from models.ranking import Ranking
from models.user import User
from config import BASELINE_DATE
import json


def calculate_change_rate(current_price: float, baseline_price: float) -> float:
    """计算涨跌幅"""
    if baseline_price is None or baseline_price == 0:
        return 0.0
    return ((current_price - baseline_price) / baseline_price) * 100


def get_or_set_baseline_price(asset: Asset, db: Session) -> Optional[float]:
    """获取或设置基准价格"""
    # 如果已有基准价格，直接返回
    if asset.baseline_price is not None:
        return asset.baseline_price
    
    # 尝试从市场数据中获取基准日的收盘价
    baseline_date_obj = date.fromisoformat(BASELINE_DATE)
    baseline_data = db.query(MarketData).filter(
        MarketData.asset_id == asset.id,
        MarketData.date == baseline_date_obj
    ).first()
    
    if baseline_data:
        asset.baseline_price = baseline_data.close_price
        db.commit()
        return baseline_data.close_price
    
    return None


def calculate_asset_rankings(target_date: date, db: Session) -> List[Dict]:
    """计算资产排名"""
    # 获取所有活跃资产
    assets = db.query(Asset).join(User).filter(User.is_active == True).all()
    
    rankings_data = []
    
    for asset in assets:
        # 获取基准价格
        baseline_price = get_or_set_baseline_price(asset, db)
        if baseline_price is None:
            continue
        
        # 获取目标日期的市场数据
        market_data = db.query(MarketData).filter(
            MarketData.asset_id == asset.id,
            MarketData.date == target_date
        ).first()
        
        if not market_data:
            continue
        
        # 计算涨跌幅
        change_rate = calculate_change_rate(market_data.close_price, baseline_price)
        
        rankings_data.append({
            "asset_id": asset.id,
            "user_id": asset.user_id,
            "change_rate": change_rate,
            "asset": asset,
            "market_data": market_data
        })
    
    # 按涨跌幅降序排序
    rankings_data.sort(key=lambda x: x["change_rate"], reverse=True)
    
    # 分配排名
    for idx, item in enumerate(rankings_data):
        item["rank"] = idx + 1
    
    return rankings_data


def calculate_user_rankings(target_date: date, db: Session) -> List[Dict]:
    """计算用户排名（基于最佳资产涨跌幅）"""
    # 获取所有活跃用户
    users = db.query(User).filter(User.is_active == True).all()
    
    user_best_rates = []
    
    for user in users:
        # 获取用户的所有资产
        assets = db.query(Asset).filter(Asset.user_id == user.id).all()
        
        best_change_rate = None
        best_asset_id = None
        
        for asset in assets:
            baseline_price = get_or_set_baseline_price(asset, db)
            if baseline_price is None:
                continue
            
            market_data = db.query(MarketData).filter(
                MarketData.asset_id == asset.id,
                MarketData.date == target_date
            ).first()
            
            if not market_data:
                continue
            
            change_rate = calculate_change_rate(market_data.close_price, baseline_price)
            
            if best_change_rate is None or change_rate > best_change_rate:
                best_change_rate = change_rate
                best_asset_id = asset.id
        
        if best_change_rate is not None:
            user_best_rates.append({
                "user_id": user.id,
                "change_rate": best_change_rate,
                "best_asset_id": best_asset_id,
                "user": user
            })
    
    # 按涨跌幅降序排序
    user_best_rates.sort(key=lambda x: x["change_rate"], reverse=True)
    
    # 分配排名
    for idx, item in enumerate(user_best_rates):
        item["rank"] = idx + 1
    
    return user_best_rates


def save_rankings(target_date: date, db: Session) -> bool:
    """计算并保存排名"""
    try:
        # 删除当天的旧排名
        db.query(Ranking).filter(Ranking.date == target_date).delete()
        
        # 计算资产排名
        asset_rankings = calculate_asset_rankings(target_date, db)
        for item in asset_rankings:
            ranking = Ranking(
                date=target_date,
                asset_id=item["asset_id"],
                user_id=item["user_id"],
                asset_rank=item["rank"],
                change_rate=item["change_rate"],
                rank_type="asset_rank"
            )
            db.add(ranking)
        
        # 计算用户排名
        user_rankings = calculate_user_rankings(target_date, db)
        for item in user_rankings:
            # 为每个用户的资产创建用户排名记录
            user_assets = db.query(Asset).filter(Asset.user_id == item["user_id"]).all()
            for asset in user_assets:
                ranking = Ranking(
                    date=target_date,
                    asset_id=asset.id,
                    user_id=item["user_id"],
                    user_rank=item["rank"],
                    change_rate=item["change_rate"],
                    rank_type="user_rank"
                )
                db.add(ranking)
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"保存排名失败: {e}")
        return False
