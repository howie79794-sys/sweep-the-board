"""模型模块（已迁移到 database/models.py）"""
# 为了向后兼容，从新位置导入
from database.models import User, Asset, MarketData, Ranking

__all__ = ["User", "Asset", "MarketData", "Ranking"]
