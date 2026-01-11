#!/bin/bash
# 启动前端开发服务器

cd "$(dirname "$0")/frontend"

# 加载nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

echo "🚀 启动前端开发服务器..."
npm run dev
