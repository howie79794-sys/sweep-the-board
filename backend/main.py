"""FastAPI 应用启动入口
极简的启动入口，负责组装各个模块
"""
import logging
import logging.config
import os
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config import CORS_ORIGINS, UPLOAD_DIR
from api.routes import router
from services.scheduler import init_scheduler, shutdown_scheduler


# ============================================================
# 日志配置
# ============================================================
# 统一用 logging 而非 print，方便 Railway 日志查看器分级、检索
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ============================================================
# Lifespan：启动 / 关闭钩子
# ============================================================
@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期：启动时挂载调度器，关闭时优雅停止。"""
    logger.info("应用启动：初始化调度器")
    init_scheduler()  # 内部根据 SCHEDULER_ENABLED 决定是否真启
    try:
        yield
    finally:
        logger.info("应用关闭：停止调度器")
        shutdown_scheduler()


# 创建FastAPI应用
app = FastAPI(
    title="CoolDown龙虎榜 API",
    description="金融资产排行榜API",
    version="1.0.0",
    lifespan=lifespan,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True if CORS_ORIGINS != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器，防止500错误导致服务崩溃"""
    logger.exception(
        "未处理的异常 path=%s method=%s type=%s msg=%s",
        request.url.path,
        request.method,
        type(exc).__name__,
        str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"内部服务器错误: {str(exc)}",
            "type": type(exc).__name__,
        },
    )

# 挂载静态文件（头像）
app.mount("/avatars", StaticFiles(directory=str(UPLOAD_DIR)), name="avatars")

# 注册路由
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "CoolDown龙虎榜 API", "version": "1.0.0"}


@app.get("/api/health")
async def health():
    return {"status": "ok"}
