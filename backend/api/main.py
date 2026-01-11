"""FastAPI主应用"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os

from config import CORS_ORIGINS, UPLOAD_DIR

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

# 挂载静态文件（头像）
app.mount("/avatars", StaticFiles(directory=str(UPLOAD_DIR)), name="avatars")

# 导入路由
from api.routes import users, assets, data, ranking

app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(assets.router, prefix="/api/assets", tags=["assets"])
app.include_router(data.router, prefix="/api/data", tags=["data"])
app.include_router(ranking.router, prefix="/api/ranking", tags=["ranking"])


@app.get("/")
async def root():
    return {"message": "CoolDown龙虎榜 API", "version": "1.0.0"}


@app.get("/api/health")
async def health():
    return {"status": "ok"}
