#!/bin/bash
# 启动脚本：同时启动前后端服务

set -e

echo "🚀 启动 CoolDown龙虎榜服务..."

# 创建数据目录（用于头像文件存储）
mkdir -p /app/data/avatars

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
cd /app/backend
echo "📦 初始化数据库表结构..."
PYTHONPATH=/app/backend python3 -m database.init_db || {
    echo "⚠️  数据库表结构创建失败，请检查数据库连接"
    exit 1
}

# 启动后端 FastAPI（后台运行，端口 8000）
echo "🔧 启动后端 API (端口 8000)..."
cd /app/backend
PYTHONPATH=/app/backend uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 等待后端启动
sleep 5

# 检查后端是否启动成功（最多重试3次）
for i in {1..3}; do
    if curl -s http://localhost:8000/api/health > /dev/null; then
        echo "✅ 后端启动成功"
        break
    fi
    if [ $i -eq 3 ]; then
        echo "❌ 后端启动失败，尝试继续..."
    else
        echo "⏳ 等待后端启动... ($i/3)"
        sleep 2
    fi
done

# 启动前端 Next.js（前台运行，端口 7860，Hugging Face 标准端口）
echo "🎨 启动前端服务 (端口 7860)..."
cd /app/frontend
PORT=7860 HOSTNAME=0.0.0.0 npm run start &
FRONTEND_PID=$!

# 等待前端启动
sleep 5

echo "✅ 服务启动完成"
echo "   - 前端: http://localhost:7860"
echo "   - 后端: http://localhost:8000"

# 保持容器运行，等待任一进程退出
wait
