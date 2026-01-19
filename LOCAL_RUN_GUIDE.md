# 本地运行指南

## 快速开始（5分钟）

### 1️⃣ 前置准备

确保已安装：
- ✅ Python 3.8+
- ✅ Node.js 18+
- ✅ PostgreSQL（或使用 Supabase 云端数据库）

### 2️⃣ 设置环境变量

创建 `.env` 文件或导出环境变量：

```bash
# 数据库连接（必填）
export DATABASE_URL='your_database_url'

# Supabase Storage（可选，用于头像上传）
export SUPABASE_URL='your_supabase_url'
export SUPABASE_SERVICE_ROLE_KEY='your_service_role_key'
```

### 3️⃣ 安装依赖

```bash
# 安装后端依赖
cd backend
pip3 install -r requirements.txt
cd ..

# 安装前端依赖
cd frontend
npm install
cd ..
```

### 4️⃣ 启动服务

**方法 1：一键启动（推荐）**
```bash
./start.sh
```

**方法 2：分别启动**
```bash
# 终端 1：启动后端
./start_backend.sh

# 终端 2：启动前端
./START_FRONTEND.sh
```

**方法 3：使用 Python 入口**
```bash
python3 app.py
```

### 5️⃣ 访问服务

- 🎨 前端：http://localhost:7860
- 🔧 后端：http://localhost:8000
- 📚 API 文档：http://localhost:8000/docs

## 故障排除

### ❌ 错误：`FileNotFoundError: [Errno 2] No such file or directory: '/app'`

**原因**：旧版本代码硬编码了 `/app` 路径

**解决方案**：已修复！确保使用最新版本的 `app.py` 和 `start.sh`

验证修复：
```bash
python3 -c "
import os
from pathlib import Path
if os.path.exists('/app'):
    print('云端环境')
else:
    print('本地环境 ✅')
"
```

### ❌ 错误：`DATABASE_URL 环境变量未设置`

**解决方案**：
```bash
export DATABASE_URL='postgresql://user:pass@host:5432/dbname'
# 或使用 Supabase
export DATABASE_URL='postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres'
```

### ❌ 错误：端口被占用

**解决方案**：
```bash
# 查找占用端口的进程
lsof -i :8000
lsof -i :7860

# 杀死进程
kill -9 <PID>
```

### ❌ 错误：`npm: command not found`

**解决方案**：
```bash
# 安装 Node.js（使用 nvm）
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18
```

## 开发模式 vs 生产模式

### 开发模式（推荐用于本地调试）

```bash
# 后端：自动重载
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 前端：自动重载
cd frontend
npm run dev
```

### 生产模式

```bash
# 前端：构建并启动
cd frontend
npm run build
PORT=7860 npm run start
```

## 目录结构

```
.
├── app.py              # 主入口文件（支持本地和云端）✅
├── start.sh            # 启动脚本（支持本地和云端）✅
├── backend/
│   ├── main.py         # FastAPI 应用
│   ├── config.py       # 配置文件（使用相对路径）✅
│   ├── requirements.txt
│   └── ...
├── frontend/
│   ├── package.json
│   └── ...
└── data/
    └── avatars/        # 头像存储目录
```

## 环境检测说明

项目会自动检测运行环境：

**云端环境（Docker）**：
- 检测到 `/app` 目录存在
- 自动使用 `/app` 作为项目根目录

**本地环境**：
- 未检测到 `/app` 目录
- 自动使用脚本所在目录作为项目根目录

查看当前环境：
```bash
./start.sh | grep "运行环境"
```

## 数据库初始化

首次运行时，系统会自动初始化数据库表结构：

```bash
cd backend
python3 -m database.init_db
```

## 数据迁移（如果需要）

如果你已经有旧的数据库，可能需要执行迁移：

```bash
# 添加 is_core 字段
sqlite3 data/yqt.db < backend/database/migrations/001_add_is_core.sql

# 执行数据迁移
cd backend
python scripts/migrate_is_core.py
```

## 管理界面

访问 http://localhost:7860/admin 进行：
- 用户管理
- 资产管理
- 数据更新

## API 测试

使用 FastAPI 自动生成的交互式文档：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 日志查看

```bash
# 后端日志
tail -f backend/logs/app.log

# 前端日志
# 直接在启动终端查看
```

## 停止服务

```bash
# Ctrl+C 停止前台进程

# 或者杀死后台进程
pkill -f "uvicorn main:app"
pkill -f "next dev"
```

## 性能优化建议

1. **使用生产模式**：前端构建后性能更好
2. **配置反向代理**：使用 Nginx 代理前后端
3. **启用缓存**：配置 Redis 缓存热点数据
4. **数据库索引**：确保关键字段已建立索引

## 相关文档

- [路径修复总结](./PATH_FIX_SUMMARY.md)
- [资产分级功能迁移指南](./MIGRATION_IS_CORE.md)
- [快速开始指南](./QUICKSTART_IS_CORE.md)

## 获取帮助

如遇问题，请检查：
1. ✅ 环境变量是否正确设置
2. ✅ 依赖是否完整安装
3. ✅ 端口是否被占用
4. ✅ 数据库连接是否正常

---

**提示**：如果一切正常，你应该能看到：
```
✅ 后端服务已就绪
✅ 服务启动完成
   - 前端: http://localhost:7860
   - 后端: http://localhost:8000
```

祝你开发顺利！🚀
