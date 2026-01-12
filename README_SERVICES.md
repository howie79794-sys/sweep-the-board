# 服务启动指南

## 问题说明

如果您访问 `localhost:8000`，您会看到后端API的响应（JSON格式）。

要访问前端页面，请访问 **`localhost:3000`**。

## 启动服务

### 方法1：分别启动（推荐）

#### 1. 启动后端服务

```bash
cd backend
PYTHONPATH=. uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. 启动前端服务（新终端窗口）

```bash
cd frontend
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
npm run dev
```

### 方法2：使用启动脚本

```bash
# 启动前端
./START_FRONTEND.sh
```

## 访问地址

- **前端页面**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

## 注意事项

- 前端服务运行在 **3000端口**
- 后端API运行在 **8000端口**
- 两个服务需要**同时运行**
- 访问前端页面时，浏览器地址栏应该显示 `localhost:3000`

## 检查服务状态

```bash
# 检查后端
curl http://localhost:8000/api/health

# 检查前端
curl http://localhost:3000
```
