"""资产核心字段迁移脚本

1) 新增 assets.is_core 字段（如不存在）
2) 批量回填：每个 user_id 仅保留一个核心资产（最小 id）
"""
from sqlalchemy import text

from database.config import engine, SessionLocal


def ensure_is_core_column() -> None:
    """确保 assets.is_core 字段存在。"""
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE assets ADD COLUMN IF NOT EXISTS is_core BOOLEAN DEFAULT FALSE")
        )


def backfill_core_assets() -> None:
    """回填核心资产：每个用户仅保留一个核心资产（最小 id）。"""
    db = SessionLocal()
    try:
        db.execute(text("UPDATE assets SET is_core = FALSE"))
        db.execute(
            text(
                """
                UPDATE assets
                SET is_core = TRUE
                WHERE id IN (
                    SELECT MIN(id)
                    FROM assets
                    GROUP BY user_id
                )
                """
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("[迁移] 开始新增 is_core 字段...")
    ensure_is_core_column()
    print("[迁移] 开始回填核心资产...")
    backfill_core_assets()
    print("[迁移] ✓ 迁移完成")
