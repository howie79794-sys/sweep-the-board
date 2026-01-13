#!/bin/bash
# CoolDown龙虎榜 - 启动脚本

# 加载nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "🚀 启动CoolDown龙虎榜服务..."
echo ""

# 启动后端
echo "📦 启动后端API服务器..."
cd "$SCRIPT_DIR/backend"
PYTHONPATH=. uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "   后端PID: $BACKEND_PID"
echo "   API地址: http://localhost:8000"
echo "   API文档: http://localhost:8000/docs"
echo ""

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

# 启动前端
echo "🎨 启动前端开发服务器..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
echo "   前端PID: $FRONTEND_PID"
echo "   前端地址: http://localhost:3000"
echo ""

echo "✅ 服务已启动！"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

# 等待用户中断
wait
