"""配置文件"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR}/data/database.db"
)

# API配置
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# 文件上传配置
UPLOAD_DIR = BASE_DIR / "data" / "avatars"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# CORS配置 - 允许所有来源（在生产环境中更灵活）
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "*"  # 在生产环境中允许所有来源，或使用环境变量配置
).split(",") if "," in os.getenv("CORS_ORIGINS", "*") else ["*"]

# 基准日期
BASELINE_DATE = "2026-01-05"
START_DATE = "2026-01-06"
END_DATE = "2026-12-31"
