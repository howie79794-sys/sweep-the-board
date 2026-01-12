# CoolDown龙虎榜 - 后端API

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

设置环境变量 `DATABASE_URL` 为 Supabase 数据库连接字符串：

```bash
export DATABASE_URL="postgresql://user:password@host:port/database"
```

### 3. 初始化数据库表结构

```bash
python3 -m database.init_db
```

这将创建数据库表结构（如果不存在）。**注意：不会创建任何测试数据，所有数据需通过管理界面手动创建。**

### 4. 启动服务器

```bash
PYTHONPATH=. python3 run.py
```

或者使用uvicorn：

```bash
PYTHONPATH=. uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. 访问API文档

启动服务器后，访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 6. API端点

- `GET /api/health` - 健康检查
- `GET /api/users` - 获取用户列表
- `GET /api/assets` - 获取资产列表
- `GET /api/ranking` - 获取排名
- `POST /api/data/update` - 更新数据

### 环境变量

- `DATABASE_URL`: **必需** - Supabase PostgreSQL 数据库连接字符串（格式：`postgresql://user:password@host:port/database`）
- `API_HOST`: API主机（默认：0.0.0.0）
- `API_PORT`: API端口（默认：8000）

**重要提示：**
- 数据库连接使用 Supabase（PostgreSQL），不再支持本地 SQLite
- 必须配置 `DATABASE_URL` 环境变量，否则应用无法启动
- 数据库初始化脚本仅创建表结构，不会创建任何测试数据
