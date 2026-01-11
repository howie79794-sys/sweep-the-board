from sqlalchemy import Column, Integer, Float, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.base import Base


class Ranking(Base):
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
