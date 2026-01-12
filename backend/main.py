"""FastAPI 应用启动入口
极简的启动入口，负责组装各个模块
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path
import os
import traceback

from config import CORS_ORIGINS, UPLOAD_DIR
from api.routes import router

# 创建FastAPI应用
app = FastAPI(
    title="CoolDown龙虎榜 API",
    description="金融资产排行榜API",
    version="1.0.0"
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
    print(f"[API] 未处理的异常: {type(exc).__name__}: {str(exc)}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"内部服务器错误: {str(exc)}",
            "type": type(exc).__name__
        }
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
