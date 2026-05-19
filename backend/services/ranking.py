"""排名计算服务
专门存放计算龙虎榜排名的业务逻辑
"""
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta, timezone
from typing import List, Dict, Optional
import time

from database.models import Asset, MarketData, Ranking, User
from config import BASELINE_DATE


def get_beijing_date() -> date:
    """获取当前北京时间的日期"""
    utc_now = datetime.now(timezone.utc)
    beijing_tz = timezone(timedelta(hours=8))
    beijing_time = utc_now.astimezone(beijing_tz)
    return beijing_time.date()


def get_weekly_baseline_date() -> date:
    """
    获取自然周榜单的基准日期（上周五或最近的有效交易日）
    以北京时间为准，本周的基准价为上周五收盘价
    """
    today = get_beijing_date()
    # 当前周的周一
    current_monday = today - timedelta(days=today.weekday())
    # 上周五 = 当前周一 - 3 天
    last_friday = current_monday - timedelta(days=3)
    return last_friday


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
    """
    计算用户排名

    规则（重要）：
        用户的代表涨跌幅 = 该用户「核心资产」(is_core=True) 的累计涨跌幅。
        这与首页"核心资产龙虎榜"、"核心资产明细表"、"自然周榜单"完全一致。

    历史 bug：
        旧逻辑取 "该用户所有资产中涨跌幅最高的那个"。当用户拥有多个非核心资产时，
        会导致龙虎榜显示的 change_rate 与明细表不一致（用户 ID=1 吴斯克为典型案例：
        龙虎榜显示 60% 但明细表显示 24%）。

    降级策略：
        如果用户没有标记 is_core 的资产，回退到「涨跌幅最高的资产」，保证用户
        仍可入榜（避免显示 "暂无数据"）。
    """
    # 获取所有活跃用户
    users = db.query(User).filter(User.is_active == True).all()

    user_best_rates = []
    users_without_rate = []

    for user in users:
        # 获取用户的所有资产
        assets = db.query(Asset).filter(Asset.user_id == user.id).all()

        # 主路径：仅核心资产
        core_change_rate = None
        core_asset_id = None
        # 降级路径：最强资产（仅当无核心资产时使用）
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

            # 核心资产：直接锁定（一人一心，理论上只有一个）
            if asset.is_core:
                core_change_rate = change_rate
                core_asset_id = asset.id

            # 同时跟踪"最强资产"作为降级
            if best_change_rate is None or change_rate > best_change_rate:
                best_change_rate = change_rate
                best_asset_id = asset.id

        # 优先用核心资产；没有核心则用最强
        selected_change_rate = core_change_rate if core_change_rate is not None else best_change_rate
        selected_asset_id = core_asset_id if core_asset_id is not None else best_asset_id

        if selected_change_rate is not None:
            user_best_rates.append({
                "user_id": user.id,
                "change_rate": selected_change_rate,
                "best_asset_id": selected_asset_id,
                "user": user,
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


def get_asset_weekly_baseline_price(asset_id: int, baseline_date: date, db: Session) -> Optional[float]:
    """
    获取资产在基准日（或基准日之前最近有效交易日）的收盘价
    用于自然周榜单的基准价计算
    """
    baseline_data = db.query(MarketData).filter(
        MarketData.asset_id == asset_id,
        MarketData.date <= baseline_date
    ).order_by(MarketData.date.desc()).first()
    if baseline_data:
        return baseline_data.close_price
    return None


def calculate_weekly_rankings(db: Session) -> List[Dict]:
    """
    计算自然周榜单（核心资产本周表现）
    基准价：上周五（或最近有效交易日）收盘价
    收益率 = (现价 - 基准价) / 基准价
    返回按涨跌幅降序排列的列表
    """
    baseline_date = get_weekly_baseline_date()
    # 获取最新交易日（现价日期）
    from services.market_data import get_latest_trading_date
    latest_date = get_latest_trading_date(db)

    # 获取所有活跃的核心资产
    assets = db.query(Asset).join(User).filter(
        User.is_active == True,
        Asset.is_core == True
    ).all()

    results = []
    for asset in assets:
        baseline_price = get_asset_weekly_baseline_price(asset.id, baseline_date, db)
        if baseline_price is None or baseline_price <= 0:
            continue

        current_data = db.query(MarketData).filter(
            MarketData.asset_id == asset.id,
            MarketData.date <= latest_date
        ).order_by(MarketData.date.desc()).first()
        if not current_data:
            continue

        current_price = current_data.close_price
        change_rate = ((current_price - baseline_price) / baseline_price) * 100

        results.append({
            "asset_id": asset.id,
            "code": asset.code,
            "name": asset.name,
            "change_rate": change_rate,
            "current_price": current_price,
            "baseline_price": baseline_price,
            "baseline_date": baseline_date.isoformat(),
            "user": {
                "id": asset.user.id,
                "name": asset.user.name,
                "avatar_url": asset.user.avatar_url,
            },
            "asset": asset,
        })

    # 按涨跌幅降序排序
    results.sort(key=lambda x: x["change_rate"], reverse=True)
    return results


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
