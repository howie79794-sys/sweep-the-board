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

        # 已成功写入的资产保留；任何资产失败都必须反映在工作流状态中。
        for item in result.get("details", []):
            if not item["result"].get("success"):
                logger.error("未更新 %s: %s", item["asset_name"], item["result"].get("message"))
        if summary["failed"] > 0 or summary["total"] == 0 or result.get("error"):
            logger.error("存在未取得有效行情的资产，不能将本次运行判定为全部成功")
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
