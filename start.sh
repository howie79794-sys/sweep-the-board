#!/bin/bash
# 启动脚本：同时启动前后端服务
# 支持本地和云端运行环境

set -e

echo "🚀 启动 CoolDown龙虎榜服务..."

# 检测项目根目录（适配本地和云端）
if [ -d "/app" ] && [ -d "/app/backend" ]; then
    # 云端环境（Docker）
    APP_ROOT="/app"
    echo "📍 运行环境: 云端 (Docker)"
else
    # 本地环境
    APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    echo "📍 运行环境: 本地开发"
fi

echo "📂 项目根目录: $APP_ROOT"

# 创建数据目录（用于头像文件存储）
mkdir -p "$APP_ROOT/data/avatars"

# 检查数据库连接配置
echo "📁 检查数据库配置..."
if [ -z "$DATABASE_URL" ]; then
    echo "   ❌ 错误: DATABASE_URL 环境变量未设置"
    echo "   📌 请配置 Supabase 数据库连接字符串"
    exit 1
else
    echo "   ✓ DATABASE_URL 已配置（使用 Supabase 远程数据库）"
fi

# 初始化数据库表结构（仅创建表，不创建任何测试数据）
cd "$APP_ROOT/backend"
echo "📦 初始化数据库表结构..."
PYTHONPATH="$APP_ROOT/backend" python3 -m database.init_db || {
    echo "⚠️  数据库表结构创建失败，请检查数据库连接"
    exit 1
}

# 启动后端 FastAPI（后台运行，端口 8000）
echo "🔧 启动后端 API (端口 8000)..."
cd "$APP_ROOT/backend"
PYTHONPATH="$APP_ROOT/backend" uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 等待后端启动并检查健康状态
echo "⏳ 等待后端服务启动..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "✅ 后端服务已就绪"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ 后端服务启动失败，请检查后端日志"
        echo "   尝试访问: http://localhost:8000/api/health"
        exit 1
    fi
    echo "   等待后端启动... ($i/30)"
    sleep 1
done
echo ""

# 启动前端 Next.js（前台运行，端口 7860，Hugging Face 标准端口）
echo "🎨 启动前端服务 (端口 7860)..."
cd "$APP_ROOT/frontend"
PORT=7860 HOSTNAME=0.0.0.0 npm run start &
FRONTEND_PID=$!

# 等待前端启动
sleep 5

echo "✅ 服务启动完成"
echo "   - 前端: http://localhost:7860"
echo "   - 后端: http://localhost:8000"

# 保持容器运行，等待任一进程退出
wait
