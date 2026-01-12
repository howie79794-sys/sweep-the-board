"""配置文件"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 数据库配置（从环境变量读取，必须配置）
# 注意：DATABASE_URL 在 database/base.py 中处理，这里不再重复定义

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
START_DATE = "2026-01-05"
END_DATE = "2026-12-31"

# Supabase Storage 配置
# 确保去除空格和换行符，避免连接错误
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip() if os.getenv("SUPABASE_URL") else None
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() if os.getenv("SUPABASE_SERVICE_ROLE_KEY") else None
