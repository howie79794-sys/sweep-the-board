"""GitHub Actions 定时行情更新入口。

该脚本替代常驻容器里的 APScheduler：执行一次完整更新、保存排名后退出。
所有业务数据仍写入 Supabase，不依赖运行器本地文件。
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import date
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database.config import SessionLocal  # noqa: E402
from services.market_data import update_all_assets_data  # noqa: E402
from services.ranking import save_rankings  # noqa: E402


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("scheduled-market-data-update")


def main() -> int:
    db = SessionLocal()
    try:
        logger.info("开始执行定时行情更新")
        result = update_all_assets_data(db, force=False)

        logger.info("开始保存当日排名")
        save_rankings(date.today(), db)

        summary = {
            "total": result.get("total", 0),
            "success": result.get("success", 0),
            "failed": result.get("failed", 0),
        }
        logger.info("定时行情更新完成: %s", json.dumps(summary, ensure_ascii=False))

        # 单点失败会在下一次定时任务中继续重试；只有全部失败才让工作流失败，
        # 避免外部行情源的短暂波动制造持续红灯。
        if summary["total"] > 0 and summary["success"] == 0:
            logger.error("所有资产更新均失败")
            return 1
        return 0
    except Exception:
        logger.exception("定时行情更新发生未捕获异常")
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
