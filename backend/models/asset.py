from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.base import Base


class Asset(Base):
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    user = relationship("User", back_populates="assets")
    market_data = relationship("MarketData", back_populates="asset", cascade="all, delete-orphan")
    rankings = relationship("Ranking", back_populates="asset")
