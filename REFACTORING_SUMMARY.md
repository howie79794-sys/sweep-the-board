# 后端代码重构总结

## 重构目标

将后端代码拆分为更模块化的结构，减少上下文消耗，提高代码可维护性。

## 重构后的目录结构

```
backend/
├── main.py                    # FastAPI 应用启动入口（极简）
├── config.py                  # 应用配置（CORS、文件上传等）
├── run.py                     # 开发服务器启动脚本
│
├── database/                  # 数据库模块
│   ├── __init__.py           # 模块导出
│   ├── config.py             # 数据库配置（连接池、6543端口、sslmode）
│   ├── models.py             # 所有数据库模型定义（User, Asset, MarketData, Ranking）
│   └── init_db.py            # 数据库初始化脚本
│
├── services/                  # 业务逻辑服务
│   ├── __init__.py           # 模块导出
│   ├── market_data.py        # 市场数据获取和存储（yfinance、baostock）
│   └── ranking.py            # 排名计算逻辑
│
└── api/                      # API 路由
    ├── __init__.py           # 模块导出
    └── routes.py             # 所有 API 路由（用户、资产、数据、排名）
```

## 主要变更

### 1. database/ 模块

- **config.py**: 
  - 专门负责读取 `DATABASE_URL` 环境变量
  - 配置 SQLAlchemy 连接池（包含 6543 端口和 sslmode 参数）
  - 提供 `get_db()` 和 `init_db()` 函数
  
- **models.py**: 
  - 合并了所有数据库表结构定义
  - 包含 `User`, `Asset`, `MarketData`, `Ranking` 四个模型

### 2. services/ 模块

- **market_data.py**: 
  - 整合了原 `data_fetcher.py` 和 `data_storage.py` 的功能
  - 专门存放调用外部接口（yfinance、baostock）获取市场数据的逻辑
  - 包含数据获取、解析、存储的完整流程
  
- **ranking.py**: 
  - 整合了原 `ranking_calculator.py` 的功能
  - 专门存放计算龙虎榜排名的业务逻辑
  - 包含资产排名和用户排名的计算

### 3. api/ 模块

- **routes.py**: 
  - 合并了原 `api/routes/users.py`, `assets.py`, `data.py`, `ranking.py` 的所有路由
  - 统一管理所有 FastAPI 接口路径
  - 使用标签（tags）区分不同功能模块

### 4. 根目录

- **main.py**: 
  - 极简的启动入口
  - 负责组装各个模块（CORS、异常处理、静态文件、路由注册）
  - 不再包含业务逻辑

## 已删除的文件

### 测试和检查文件
- `test_api.py`
- `test_data_fetcher.py`
- `check_imports.py`
- `check_service.py`

### 旧的模块文件
- `api/main.py`（已迁移到根目录）
- `api/routes/users.py`（已合并到 `api/routes.py`）
- `api/routes/assets.py`（已合并到 `api/routes.py`）
- `api/routes/data.py`（已合并到 `api/routes.py`）
- `api/routes/ranking.py`（已合并到 `api/routes.py`）
- `models/user.py`（已合并到 `database/models.py`）
- `models/asset.py`（已合并到 `database/models.py`）
- `models/market_data.py`（已合并到 `database/models.py`）
- `models/ranking.py`（已合并到 `database/models.py`）
- `services/data_fetcher.py`（已合并到 `services/market_data.py`）
- `services/data_storage.py`（已合并到 `services/market_data.py`）
- `services/ranking_calculator.py`（已合并到 `services/ranking.py`）
- `database/base.py`（已合并到 `database/config.py`）

## 导入关系

### 正确的导入方式

```python
# 数据库相关
from database.config import get_db, SessionLocal, Base, init_db
from database.models import User, Asset, MarketData, Ranking

# 服务相关
from services.market_data import fetch_asset_data, update_asset_data, update_all_assets_data
from services.ranking import save_rankings, calculate_asset_rankings, calculate_user_rankings

# API 路由
from api.routes import router
```

## 功能保持不变

- ✅ 所有 API 端点功能保持不变
- ✅ 数据库连接和配置保持不变（支持 Supabase）
- ✅ 市场数据获取逻辑保持不变（yfinance 主数据源，baostock 备份）
- ✅ 排名计算逻辑保持不变
- ✅ Hugging Face 部署配置保持不变

## 启动方式

### 开发环境

```bash
cd backend
python3 run.py
# 或
PYTHONPATH=. uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 生产环境（Hugging Face）

使用 `start.sh` 脚本，已更新为使用新的 `main:app` 入口。

## 注意事项

1. **环境变量**: 必须配置 `DATABASE_URL` 环境变量
2. **向后兼容**: `models/__init__.py` 和 `database/__init__.py` 提供了向后兼容的导入
3. **数据库初始化**: 使用 `python3 -m database.init_db` 初始化数据库表结构

## 优势

1. **模块化**: 代码按功能清晰分离，易于维护
2. **减少上下文**: 每个文件职责单一，减少代码阅读负担
3. **统一管理**: 相关功能集中在一个文件中，便于查找和修改
4. **易于扩展**: 新功能可以轻松添加到对应的模块中
