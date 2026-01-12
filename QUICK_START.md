# CoolDown龙虎榜 - 快速启动指南

## ✅ Node.js 已安装

- Node.js版本: v24.12.0
- npm版本: v11.6.2
- 前端依赖: 已安装

## 🚀 启动服务

### 方法1：使用启动脚本（推荐）

```bash
./START_SERVERS.sh
```

### 方法2：手动启动

#### 启动后端

```bash
cd backend
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
PYTHONPATH=. uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### 启动前端（新终端窗口）

```bash
cd frontend
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
npm run dev
```

## 📍 访问地址

- **前端界面**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/api/health

## 🔍 验证服务状态

### 检查后端
```bash
curl http://localhost:8000/api/health
```

### 检查前端
```bash
curl http://localhost:3000
```

### 检查API端点
```bash
# 获取用户列表
curl http://localhost:8000/api/users

# 获取资产列表
curl http://localhost:8000/api/assets

# 获取排名
curl http://localhost:8000/api/ranking
```

## ⚙️ 环境配置

### 永久配置nvm（添加到 ~/.zshrc 或 ~/.bashrc）

nvm已经自动添加到 ~/.zshrc，如果您使用bash，请添加到 ~/.bashrc：

```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
```

然后重新加载配置：
```bash
source ~/.zshrc  # 或 source ~/.bashrc
```

## 🛠️ 常见问题

### 问题1：找不到node或npm命令

**解决方案**：
```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
```

或者重新打开终端窗口。

### 问题2：端口被占用

**解决方案**：
- 后端端口8000被占用：修改 `backend/config.py` 中的 `API_PORT`
- 前端端口3000被占用：Next.js会自动使用下一个可用端口

### 问题3：前端无法连接后端

**解决方案**：
1. 确保后端正在运行
2. 检查 `frontend/lib/api.ts` 中的 `API_BASE_URL` 配置
3. 检查CORS设置（后端已配置允许localhost:3000）

## 📝 下一步

1. 在浏览器中访问 http://localhost:3000 查看前端界面
2. 访问 http://localhost:8000/docs 查看API文档
3. 测试前后端集成功能
