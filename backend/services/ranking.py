"""排名计算服务
专门存放计算龙虎榜排名的业务逻辑
"""
from sqlalchemy.orm import Session
from datetime import date
from typing import List, Dict, Optional

from database.models import Asset, MarketData, Ranking, User
from config import BASELINE_DATE


def calculate_change_rate(current_price: float, baseline_price: float) -> float:
    """计算涨跌幅"""
    if baseline_price is None or baseline_price == 0:
        return 0.0
    return ((current_price - baseline_price) / baseline_price) * 100


def get_or_set_baseline_price(asset: Asset, db: Session) -> Optional[float]:
    """获取或设置基准价格（如果基准日期没有数据，自动寻找之后的第一个交易日）"""
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
        asset.baseline_date = baseline_date_obj
        db.commit()
        print(f"[排名计算] 资产 {asset.name} 基准价格: {baseline_data.close_price} (日期: {baseline_date_obj})")
        return baseline_data.close_price
    
    # 如果基准日期没有数据，寻找该日期之后的第一个有数据的交易日
    print(f"[排名计算] 资产 {asset.name} 基准日期 {baseline_date_obj} 没有数据，寻找之后的第一个交易日...")
    next_data = db.query(MarketData).filter(
        MarketData.asset_id == asset.id,
        MarketData.date >= baseline_date_obj
    ).order_by(MarketData.date.asc()).first()
    
    if next_data:
        asset.baseline_price = next_data.close_price
        asset.baseline_date = next_data.date
        db.commit()
        print(f"[排名计算] 资产 {asset.name} 使用替代基准价格: {next_data.close_price} (日期: {next_data.date})")
        return next_data.close_price
    
    print(f"[排名计算] 警告: 资产 {asset.name} 无法找到基准价格")
    return None


def calculate_asset_rankings(target_date: date, db: Session) -> List[Dict]:
    """计算资产排名（即使缺少基准价也包含资产，显示当前价格）"""
    # 获取所有活跃资产
    assets = db.query(Asset).join(User).filter(User.is_active == True).all()
    
    rankings_data = []
    rankings_with_rate = []
    rankings_without_rate = []
    
    for asset in assets:
        # 获取目标日期的市场数据（使用最新数据作为兜底）
        market_data = db.query(MarketData).filter(
            MarketData.asset_id == asset.id,
            MarketData.date <= target_date
        ).order_by(MarketData.date.desc()).first()
        
        if not market_data:
            # 如果没有目标日期的数据，仍然包含资产但标记为缺少数据
            rankings_without_rate.append({
                "asset_id": asset.id,
                "user_id": asset.user_id,
                "change_rate": None,
                "current_price": None,
                "baseline_price": None,
                "has_baseline": False,
                "has_current_data": False,
                "asset": asset,
                "market_data": None
            })
            continue
        
        # 获取基准价格
        baseline_price = get_or_set_baseline_price(asset, db)
        current_price = market_data.close_price
        
        if baseline_price is None or baseline_price == 0:
            # 缺少基准价，但仍然包含资产，显示当前价格
            rankings_without_rate.append({
                "asset_id": asset.id,
                "user_id": asset.user_id,
                "change_rate": None,
                "current_price": current_price,
                "baseline_price": None,
                "has_baseline": False,
                "has_current_data": True,
                "asset": asset,
                "market_data": market_data
            })
        else:
            # 有基准价，计算涨跌幅
            change_rate = calculate_change_rate(current_price, baseline_price)
            rankings_with_rate.append({
                "asset_id": asset.id,
                "user_id": asset.user_id,
                "change_rate": change_rate,
                "current_price": current_price,
                "baseline_price": baseline_price,
                "has_baseline": True,
                "has_current_data": True,
                "asset": asset,
                "market_data": market_data
            })
    
    # 按涨跌幅降序排序（有涨跌幅的）
    rankings_with_rate.sort(key=lambda x: x["change_rate"], reverse=True)
    
    # 分配排名（只对有涨跌幅的资产排名）
    for idx, item in enumerate(rankings_with_rate):
        item["rank"] = idx + 1
    
    # 合并结果：有排名的在前，缺少基准价的在后
    rankings_data = rankings_with_rate + rankings_without_rate
    
    print(f"[排名计算] 资产排名计算完成: 有涨跌幅 {len(rankings_with_rate)} 个，缺少基准价 {len(rankings_without_rate)} 个")
    
    return rankings_data


def calculate_user_rankings(target_date: date, db: Session) -> List[Dict]:
    """计算用户排名（基于最佳资产涨跌幅，即使缺少基准价也包含用户）"""
    # 获取所有活跃用户
    users = db.query(User).filter(User.is_active == True).all()
    
    user_best_rates = []
    users_without_rate = []
    
    for user in users:
        # 获取用户的所有资产
        assets = db.query(Asset).filter(Asset.user_id == user.id).all()
        
        best_change_rate = None
        best_asset_id = None
        has_any_rate = False
        
        for asset in assets:
            # 获取目标日期的市场数据（使用最新数据作为兜底）
            market_data = db.query(MarketData).filter(
                MarketData.asset_id == asset.id,
                MarketData.date <= target_date
            ).order_by(MarketData.date.desc()).first()
            
            if not market_data:
                continue
            
            baseline_price = get_or_set_baseline_price(asset, db)
            if baseline_price is None or baseline_price == 0:
                continue
            
            change_rate = calculate_change_rate(market_data.close_price, baseline_price)
            has_any_rate = True
            
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
        elif not has_any_rate:
            # 用户没有任何可计算的涨跌幅
            users_without_rate.append({
                "user_id": user.id,
                "change_rate": None,
                "best_asset_id": None,
                "user": user
            })
    
    # 按涨跌幅降序排序（有涨跌幅的）
    user_best_rates.sort(key=lambda x: x["change_rate"], reverse=True)
    
    # 分配排名（只对有涨跌幅的用户排名）
    for idx, item in enumerate(user_best_rates):
        item["rank"] = idx + 1
    
    # 合并结果：有排名的在前，缺少基准价的在后
    result = user_best_rates + users_without_rate
    
    print(f"[排名计算] 用户排名计算完成: 有涨跌幅 {len(user_best_rates)} 个，缺少基准价 {len(users_without_rate)} 个")
    
    return result


def save_rankings(target_date: date, db: Session) -> bool:
    """计算并保存排名"""
    try:
        # 删除当天的旧排名
        db.query(Ranking).filter(Ranking.date == target_date).delete()
        
        # 计算资产排名
        asset_rankings = calculate_asset_rankings(target_date, db)
        for item in asset_rankings:
            # 即使没有排名也保存，标记为缺少基准价
            ranking = Ranking(
                date=target_date,
                asset_id=item["asset_id"],
                user_id=item["user_id"],
                asset_rank=item.get("rank"),  # 可能为 None
                change_rate=item.get("change_rate"),  # 可能为 None
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
                    user_rank=item.get("rank"),  # 可能为 None
                    change_rate=item.get("change_rate"),  # 可能为 None
                    rank_type="user_rank"
                )
                db.add(ranking)
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"保存排名失败: {e}")
        return False
