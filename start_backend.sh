#!/bin/bash
# 启动后端服务脚本

cd "$(dirname "$0")/backend"

echo "=========================================="
echo "启动 CoolDown龙虎榜 后端服务"
echo "=========================================="
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3"
    exit 1
fi

# 检查依赖
echo "检查依赖..."
python3 -c "import yfinance, baostock, fastapi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "警告: 部分依赖可能未安装"
    echo "正在安装依赖..."
    pip3 install -q -r requirements.txt
fi

echo ""
echo "启动后端服务..."
echo "服务地址: http://localhost:8000"
echo "API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================================="
echo ""

# 启动服务
if [ -f "run.py" ]; then
    python3 run.py
else
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
fi
