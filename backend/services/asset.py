"""资产相关服务"""
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database.models import Asset


CORE_ASSET_CONFLICT_MESSAGE = "该用户已有关联的核心资产，请先取消原核心设置"


class AssetService:
    """资产相关业务逻辑服务。"""

    @staticmethod
    def ensure_single_core_asset(
        db: Session,
        user_id: int,
        is_core: bool,
        asset_id: Optional[int] = None,
    ) -> None:
        """确保同一用户只有一个核心资产。"""
        if not is_core:
            return

        query = db.query(Asset).filter(
            Asset.user_id == user_id,
            Asset.is_core == True,
        )
        if asset_id is not None:
            query = query.filter(Asset.id != asset_id)

        if query.first():
            raise HTTPException(status_code=400, detail=CORE_ASSET_CONFLICT_MESSAGE)
