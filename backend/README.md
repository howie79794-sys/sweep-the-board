# CoolDown龙虎榜 - 后端API

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
python3 -m database.init_db
```

这将创建数据库并初始化8个用户和8个资产。

### 3. 启动服务器

```bash
PYTHONPATH=. python3 run.py
```

或者使用uvicorn：

```bash
PYTHONPATH=. uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 访问API文档

启动服务器后，访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 5. API端点

- `GET /api/health` - 健康检查
- `GET /api/users` - 获取用户列表
- `GET /api/assets` - 获取资产列表
- `GET /api/ranking` - 获取排名
- `POST /api/data/update` - 更新数据

### 环境变量

- `DATABASE_URL`: 数据库URL（默认：sqlite:///../data/database.db）
- `API_HOST`: API主机（默认：0.0.0.0）
- `API_PORT`: API端口（默认：8000）
