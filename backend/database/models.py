"""数据库模型定义
存放所有数据库表结构定义（User, Asset, MarketData, Ranking）
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Float,
    Date,
    ForeignKey,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.config import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True, index=True)

    # 关系
    assets = relationship("Asset", back_populates="user", cascade="all, delete-orphan")
    rankings = relationship("Ranking", back_populates="user")


class Asset(Base):
    """资产表"""
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_type = Column(String, nullable=False)  # stock, fund, futures, forex
    market = Column(String, nullable=False)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    baseline_price = Column(Float, nullable=True)
    baseline_date = Column(Date, default="2026-01-05")
    start_date = Column(Date, default="2026-01-05")
    end_date = Column(Date, default="2026-12-31")
    is_core = Column(Boolean, default=False, nullable=False, index=True)  # 是否为核心资产（一用户一心）
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # 复合索引：龙虎榜首页常按 (user_id, is_core=True) 拉核心资产
        Index("idx_assets_user_is_core", "user_id", "is_core"),
        # 复合索引：admin 页常按 (user_id, asset_type) 过滤
        Index("idx_assets_user_type", "user_id", "asset_type"),
    )

    # 关系
    user = relationship("User", back_populates="assets")
    market_data = relationship("MarketData", back_populates="asset", cascade="all, delete-orphan")
    rankings = relationship("Ranking", back_populates="asset")
    pk_pools = relationship("PKPool", secondary="pk_pool_assets", back_populates="assets")


class PKPool(Base):
    """自定义PK池"""
    __tablename__ = "pk_pools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    assets = relationship("Asset", secondary="pk_pool_assets", back_populates="pk_pools")


class PKPoolAsset(Base):
    """PK池与资产的关联表"""
    __tablename__ = "pk_pool_assets"
    __table_args__ = (
        UniqueConstraint("pool_id", "asset_id", name="uniq_pk_pool_asset"),
    )

    id = Column(Integer, primary_key=True, index=True)
    pool_id = Column(Integer, ForeignKey("pk_pools.id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MarketData(Base):
    """市场数据表"""
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)
    turnover_rate = Column(Float, nullable=True)
    pe_ratio = Column(Float, nullable=True)
    pb_ratio = Column(Float, nullable=True)
    market_cap = Column(Float, nullable=True)
    eps_forecast = Column(Float, nullable=True)
    additional_data = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # 唯一复合索引：同一资产同一天只能有一条记录（顺便加速 (asset_id, date) 查询）
        UniqueConstraint("asset_id", "date", name="uniq_market_data_asset_date"),
        # 单列索引：日历视图、快照查询常按 date 扫
        Index("idx_market_data_date", "date"),
    )

    # 关系
    asset = relationship("Asset", back_populates="market_data")


class Ranking(Base):
    """排名表"""
    __tablename__ = "rankings"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    asset_rank = Column(Integer, nullable=True)
    user_rank = Column(Integer, nullable=True)
    change_rate = Column(Float, nullable=True)
    rank_type = Column(String, nullable=True)  # asset_rank, user_rank
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # 复合索引：首页排行榜按 (date, change_rate DESC) 排序+取前 N
        Index("idx_rankings_date_change_rate", "date", "change_rate"),
        # 用户历史排名查询：(user_id, date)
        Index("idx_rankings_user_date", "user_id", "date"),
        # 资产历史排名查询：(asset_id, date)
        Index("idx_rankings_asset_date", "asset_id", "date"),
        # 单独 date 索引（按日期切片）
        Index("idx_rankings_date", "date"),
    )

    # 关系
    asset = relationship("Asset", back_populates="rankings")
    user = relationship("User", back_populates="rankings")
