from sqlalchemy import Column, Integer, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.base import Base


class MarketData(Base):
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)
    turnover_rate = Column(Float, nullable=True)
    pe_ratio = Column(Float, nullable=True)
    market_cap = Column(Float, nullable=True)
    additional_data = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    asset = relationship("Asset", back_populates="market_data")
