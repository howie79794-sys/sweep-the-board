# 问题诊断和解决方案

## 问题现象
- HTTP 500 错误
- 用户数据和资产数据都显示为 0

## 诊断结果

### ✅ 数据库状态正常
- 数据库文件存在：`./data/database.db`
- **用户数据：8 个用户**（用户1-用户8）
- **资产数据：8 个资产**（协创数据、卧龙电驱、上海电气等）

### ❌ 问题原因
后端服务**没有运行**，导致前端无法获取数据。

## 解决方案

### 步骤 1：启动后端服务

在 `backend` 目录下运行：

```bash
cd backend
python3 run.py
```

或者使用 uvicorn 直接启动：

```bash
cd backend
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 步骤 2：验证后端服务

打开浏览器访问：
- http://localhost:8000/api/health - 应该返回 `{"status": "ok"}`
- http://localhost:8000/api/users - 应该返回 8 个用户
- http://localhost:8000/api/assets - 应该返回 8 个资产

### 步骤 3：刷新前端页面

确保前端也在运行（通常应该在 http://localhost:3000），然后刷新管理界面页面。

## 快速启动脚本

可以创建一个启动脚本 `start_backend.sh`：

```bash
#!/bin/bash
cd "$(dirname "$0")/backend"
python3 run.py
```

然后运行：
```bash
chmod +x start_backend.sh
./start_backend.sh
```

## 已修复的问题

1. ✅ 添加了全局异常处理器，防止 500 错误导致服务崩溃
2. ✅ 数据库状态检查脚本已创建（`backend/check_service.py`）
3. ✅ 数据获取服务已更新为使用 yfinance 和 baostock

## 验证数据存在

运行以下命令验证数据：

```bash
cd backend
python3 check_service.py
```

应该看到：
- ✓ 数据库连接成功
- 用户数据: 8 个用户
- 资产数据: 8 个资产
