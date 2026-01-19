"""数据库模型定义
存放所有数据库表结构定义（User, Asset, MarketData, Ranking）
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Date, ForeignKey, Text, UniqueConstraint
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
    is_active = Column(Boolean, default=True)

    # 关系
    assets = relationship("Asset", back_populates="user", cascade="all, delete-orphan")
    rankings = relationship("Ranking", back_populates="user")


class Asset(Base):
    """资产表"""
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    asset_type = Column(String, nullable=False)  # stock, fund, futures, forex
    market = Column(String, nullable=False)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    baseline_price = Column(Float, nullable=True)
    baseline_date = Column(Date, default="2026-01-05")
    start_date = Column(Date, default="2026-01-05")
    end_date = Column(Date, default="2026-12-31")
    is_core = Column(Boolean, default=False, nullable=False)  # 是否为核心资产（一用户一心）
    created_at = Column(DateTime(timezone=True), server_default=func.now())

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

    # 关系
    asset = relationship("Asset", back_populates="rankings")
    user = relationship("User", back_populates="rankings")
