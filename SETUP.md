# CoolDown龙虎榜 - 设置和运行指南

## 当前状态

### ✅ 后端（已完成）

后端FastAPI服务器已成功启动并运行在 **http://localhost:8000**

- ✅ 数据库已初始化（8个用户，8个资产）
- ✅ 用户API正常工作
- ✅ API文档可访问：http://localhost:8000/docs

### ⚠️ 前端（需要Node.js）

前端需要Node.js环境，当前系统未安装Node.js。

## 快速启动指南

### 1. 后端（已在运行）

后端服务器已在后台运行。如果需要重启：

```bash
cd backend
PYTHONPATH=. uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

或使用：

```bash
cd backend
PYTHONPATH=. python3 run.py
```

### 2. 前端（需要安装Node.js）

#### 步骤1：安装Node.js

**macOS (使用Homebrew)**：
```bash
brew install node
```

**或从官网下载**：
访问 https://nodejs.org/ 下载并安装

**验证安装**：
```bash
node --version
npm --version
```

#### 步骤2：安装前端依赖

```bash
cd frontend
npm install
```

#### 步骤3：启动前端开发服务器

```bash
npm run dev
```

前端将在 http://localhost:3000 运行

### 3. 访问应用

- 前端界面：http://localhost:3000
- 后端API文档：http://localhost:8000/docs
- 后端API健康检查：http://localhost:8000/api/health

## 测试API端点

### 健康检查
```bash
curl http://localhost:8000/api/health
```

### 获取用户列表
```bash
curl http://localhost:8000/api/users
```

### 获取资产列表
```bash
curl http://localhost:8000/api/assets
```

### 获取排名
```bash
curl http://localhost:8000/api/ranking
```

## 项目结构

```
cool-down-leaderboard/
├── backend/          # Python FastAPI后端
│   ├── api/          # API路由
│   ├── models/       # 数据库模型
│   ├── services/     # 业务逻辑
│   └── database/     # 数据库配置
├── frontend/         # Next.js前端
│   ├── app/          # 页面
│   ├── components/   # 组件
│   └── lib/          # 工具函数
└── data/             # 数据存储
    ├── database.db   # SQLite数据库
    └── avatars/      # 用户头像
```

## 下一步

1. 安装Node.js
2. 安装前端依赖：`cd frontend && npm install`
3. 启动前端：`npm run dev`
4. 在浏览器中访问 http://localhost:3000
