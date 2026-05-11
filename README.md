# CoolDown 龙虎榜 · Sweep The Board

> 一个金融资产年度涨幅追踪与多人 PK 比拼平台。多人各选一支核心资产，按相对基准日的累计涨跌幅实时排名，配合丰富的图表和管理后台。

🌐 **线上访问**：<https://sweep-the-board.vercel.app>
📦 **GitHub**：<https://github.com/howie79794-sys/sweep-the-board>

---

## ✨ 功能亮点

- 🏆 **核心资产龙虎榜**：第 1/2/3 名展示金银铜奖牌，4-8 名清晰序号
- 🌡️ **涨跌热力色**：A 股惯例红涨绿跌，按强度 4 档渐变（>10% / >5% / >2% / <2%）
- 📊 **多维度可视化**：年度涨幅曲线、周度收益、PE/PB 比率、资产快照表
- 👥 **多人多资产**：每人可挂一支核心资产 + 多支辅助资产
- ⚔️ **PK 比拼池**：自定义资产对决，独立看板
- 🔁 **数据自动更新**：工作日 16:00 / 22:30 定时拉取行情，无需手动操作
- 📱 **响应式 UI**：桌面端侧边榜单 + 移动端友好布局
- 🛡️ **稳定性保障**：行情拉取自带重试 + 超时，单点失败不阻塞批量更新

---

## 🏗️ 系统架构

```
                    ┌──────────────────────────────┐
                    │   用户浏览器                  │
                    └───────────────┬──────────────┘
                                    │ HTTPS
                                    ▼
            ┌──────────────────────────────────────┐
            │  Vercel（前端 / Next.js 14）         │
            │  https://sweep-the-board.vercel.app  │
            │  - Edge CDN 全球分发                  │
            │  - SWR 客户端缓存                     │
            └───────────────┬──────────────────────┘
                            │ /api/* 代理转发
                            ▼
   ┌─────────────────────────────────────────────────┐
   │  Railway（后端 / FastAPI + Python 3.11）        │
   │  https://sweep-the-board-production.up.railway.app │
   │  - APScheduler 定时任务                          │
   │  - tenacity 行情拉取重试                         │
   └────┬──────────────────────┬─────────────────────┘
        │                      │
        ▼                      ▼
┌────────────────┐    ┌───────────────────────────┐
│ 外部行情源     │    │ Supabase                  │
│ - akshare      │    │ - PostgreSQL（业务数据）  │
│ - yfinance     │    │ - Storage（用户头像）     │
│ - baostock     │    │                           │
└────────────────┘    └───────────────────────────┘
```

### 三平台分工

| 平台 | 角色 | 关键配置 |
|------|------|---------|
| **Vercel** | 前端托管 + CDN | Root Directory: `frontend`<br>`NEXT_PUBLIC_API_URL` → Railway 域名 |
| **Railway** | Python 后端 | Root Directory: `backend`<br>Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`<br>Python 版本由 `backend/.python-version` 固定为 3.11 |
| **Supabase** | 数据库 + 文件存储 | PostgreSQL 6 张表 + `avatars` storage bucket |

---

## 🛠️ 技术栈

### 前端
- **框架**：Next.js 14.2（App Router）+ TypeScript 5.5
- **UI**：Tailwind CSS 3.4 + Radix UI + Lucide Icons
- **数据可视化**：Recharts 2.12
- **数据请求**：SWR 2.2（自动缓存、去重、后台 revalidate）
- **校验**：Zod

### 后端
- **框架**：FastAPI 0.111 + Uvicorn 0.30（standard）
- **ORM**：SQLAlchemy 2.0
- **数据库**：Supabase PostgreSQL（通过 Transaction Pooler 连接）
- **行情数据源**：
  - `akshare` ≥ 1.16（A 股、ETF、期货）
  - `yfinance` ≥ 0.2.28（美股、国际市场）
  - `baostock` ≥ 0.8.8（A 股复权数据备份）
- **容错**：`tenacity` 8.5（指数退避重试） + 线程池超时
- **定时任务**：`apscheduler` 3.10（cron 触发，时区 Asia/Shanghai）
- **存储**：`supabase-py` ≥ 2.0（头像上传）

---

## 📁 项目结构

```
sweep-the-board/
├── frontend/                          # Next.js 前端
│   ├── app/
│   │   ├── layout.tsx                 # 根布局 + SEO 元数据
│   │   ├── page.tsx                   # 首页（龙虎榜）
│   │   ├── sitemap.ts                 # 自动生成 sitemap.xml
│   │   ├── admin/page.tsx             # 管理后台
│   │   └── pk-pools/                  # PK 池页面
│   ├── components/
│   │   ├── DragonTigerBoard.tsx       # 核心资产龙虎榜（带金银铜奖牌）
│   │   ├── Leaderboard.tsx            # 综合排行榜
│   │   ├── WeeklySidebar.tsx          # 周度榜单（侧边栏）
│   │   ├── AssetSnapshotTable.tsx     # 资产快照表
│   │   ├── AllAssetsChart.tsx         # 多资产收益曲线
│   │   ├── WeeklyReturnChart.tsx      # 周度收益图
│   │   ├── PERatioChart.tsx           # PE 比率图
│   │   ├── PBRatioChart.tsx           # PB 比率图
│   │   └── ui/
│   │       ├── medal-badge.tsx        # 金银铜徽章
│   │       ├── skeleton.tsx           # 加载骨架屏
│   │       └── avatar.tsx             # 头像组件
│   ├── lib/
│   │   ├── api.ts                     # API 客户端
│   │   ├── hooks.ts                   # SWR hooks 封装
│   │   └── utils.ts                   # 工具函数（颜色、奖牌、日期）
│   ├── public/
│   │   └── robots.txt
│   ├── next.config.js                 # API 代理规则
│   └── tailwind.config.ts             # Tailwind 配置 + safelist
│
├── backend/                           # FastAPI 后端
│   ├── main.py                        # 应用入口（含 lifespan、CORS、日志）
│   ├── config.py                      # 应用配置
│   ├── .python-version                # Railway 用此固定 Python 3.11
│   ├── requirements.txt
│   ├── api/
│   │   └── routes.py                  # API 路由（users / assets / data / ranking / pk-pools）
│   ├── database/
│   │   ├── config.py                  # 数据库连接（连接池 + SSL）
│   │   ├── models.py                  # SQLAlchemy 模型 + 索引定义
│   │   ├── init_db.py                 # 表初始化
│   │   └── migrations/
│   │       ├── 001_add_is_core.sql
│   │       ├── 002_add_pk_pools.sql
│   │       ├── 003_add_pk_pool_date_range.sql
│   │       └── 004_add_indexes.sql    # 性能索引（手动执行）
│   └── services/
│       ├── market_data.py             # 行情拉取主逻辑
│       ├── ranking.py                 # 排名计算
│       ├── asset.py                   # 资产业务逻辑
│       ├── storage.py                 # 文件存储（Supabase Storage）
│       ├── scheduler.py               # APScheduler 定时任务
│       └── _resilience.py             # 重试 + 超时装饰器
│
├── data/
│   └── avatars/                       # 本地头像缓存（gitignored）
│
└── README.md                          # 本文档
```

---

## 🚀 部署指南

### 准备工作

1. **GitHub 仓库**：已托管在 <https://github.com/howie79794-sys/sweep-the-board>
2. **Supabase 项目**：创建 PostgreSQL 数据库 + 名为 `avatars` 的 storage bucket
3. **Vercel 账号**：用于前端部署
4. **Railway 账号**：用于后端部署

### Step 1: Railway 后端部署

1. Railway 控制台 → **New Project → Deploy from GitHub repo** → 选择本仓库
2. 进入 Service → **Settings**：
   - **Source** 区块：
     - **Root Directory**：`backend`（不带前导斜杠）
   - **Deploy** 区块：
     - **Start Command**：`uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Networking** 区块：点 **Generate Domain** 获取公开域名
3. 进入 Service → **Variables**，添加：

   | 变量名 | 值 |
   |--------|-----|
   | `SUPABASE_URL` | `https://<project-ref>.supabase.co` |
   | `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Project Settings → API → service_role key |
   | `DATABASE_URL` | `postgresql://postgres.<project-ref>:<密码>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require` |
   | `SCHEDULER_ENABLED` | `true`（启用定时数据更新） |
   | `LOG_LEVEL` | `INFO` |

   > ⚠️ **DATABASE_URL 关键点**：
   > - 必须用 **Transaction Pooler** 地址（端口 `6543`），而非直连地址
   >   ：Railway 免费套餐不支持 IPv6，直连地址会解析为 IPv6 失败
   > - 用户名格式必须是 `postgres.<project-ref>`（Pooler 多租户识别要求）
   > - 末尾必须带 `?sslmode=require`

4. Railway 会自动重新部署。访问 `https://<your-railway-domain>/api/health`，看到 `{"status":"ok"}` 即成功。

### Step 2: Vercel 前端部署

1. Vercel 控制台 → **Add New Project → Import Git Repository** → 选择本仓库
2. **Configure Project**：
   - **Root Directory**：`frontend`
   - **Framework Preset**：Next.js（自动识别）
3. **Environment Variables**：

   | 变量名 | 值 |
   |--------|-----|
   | `NEXT_PUBLIC_API_URL` | Step 1 拿到的 Railway 域名，如 `https://xxxx.up.railway.app` |
   | `NEXT_PUBLIC_SITE_URL` | Vercel 给的前端域名（用于 SEO sitemap，可选） |

4. 点 **Deploy**。完成后访问 Vercel 域名验证。

### Step 3: Supabase 性能索引（一次性操作）

新部署后，需要在 Supabase 加一次性能索引：

1. Supabase 控制台 → **SQL Editor**
2. 复制 `backend/database/migrations/004_add_indexes.sql` 全部内容粘进去
3. 点 **Run**

文件中所有语句都是 `CREATE INDEX IF NOT EXISTS`，可重复执行、不会锁表、不会破坏数据。

### Step 4: 验证

```bash
# 后端在线
curl https://<your-railway-domain>/api/health

# 前后端链路通
curl https://<your-vercel-domain>/api/users
```

### 自动部署

两个平台都已经连接 GitHub，**push 到 `main` 分支会自动重新构建+部署**，无需手动操作。

---

## 💻 本地开发

### 环境要求

- Python 3.11+（重要：3.13 与当前 SQLAlchemy 不兼容）
- Node.js 20+
- 一个 Supabase 项目（直接复用线上的即可）

### 1. 克隆仓库

```bash
git clone https://github.com/howie79794-sys/sweep-the-board.git
cd sweep-the-board
```

### 2. 启动后端

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export SUPABASE_URL="https://<your-project>.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="<your-service-role-key>"
export DATABASE_URL="postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require"
export LOG_LEVEL="DEBUG"

# 启动（本地不要开 SCHEDULER_ENABLED，避免频繁打外部 API）
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

后端访问入口：
- API 文档（Swagger）：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/api/health>

### 3. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 设置后端地址（指向本地后端）
export NEXT_PUBLIC_API_URL="http://localhost:8000"

# 启动开发服务器
npm run dev
```

前端访问入口：
- 主页：<http://localhost:3000>
- 管理后台：<http://localhost:3000/admin>
- PK 池：<http://localhost:3000/pk-pools>

### 4. 一键启动（可选）

仓库根目录提供了 shell 脚本（前后端同时启动）：

```bash
./start.sh
```

---

## 🔧 环境变量速查

### 后端（Railway / 本地）

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `DATABASE_URL` | ✅ | - | PostgreSQL 连接串（必须 Pooler + SSL） |
| `SUPABASE_URL` | ✅ | - | Supabase 项目 URL |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | - | Supabase service_role 密钥（用于头像上传） |
| `SCHEDULER_ENABLED` | ❌ | `false` | 设 `true` 启用定时数据更新 |
| `LOG_LEVEL` | ❌ | `INFO` | 日志级别（DEBUG/INFO/WARNING/ERROR） |
| `API_HOST` | ❌ | `0.0.0.0` | 监听地址 |
| `API_PORT` | ❌ | `8000` | 监听端口（Railway 用 `$PORT`） |
| `CORS_ORIGINS` | ❌ | `*` | 允许的来源（逗号分隔） |

### 前端（Vercel / 本地）

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `NEXT_PUBLIC_API_URL` | ✅ | `http://localhost:8000` | 后端 API 地址 |
| `NEXT_PUBLIC_SITE_URL` | ❌ | `https://sweep-the-board.vercel.app` | 站点 URL（用于 SEO） |

---

## 🗄️ 数据库结构

### 表清单

| 表名 | 用途 |
|------|------|
| `users` | 用户信息（姓名、头像 URL、激活状态） |
| `assets` | 资产信息（代码、市场、基准价、是否核心） |
| `market_data` | 每日行情（收盘价、成交量、PE、PB、市值、EPS 预测） |
| `rankings` | 排名快照（按日期 / 资产 / 用户三个维度） |
| `pk_pools` | 自定义 PK 比拼池 |
| `pk_pool_assets` | PK 池与资产的多对多关联 |

### 关键索引（migrations/004）

- `assets`: `(user_id, is_core)` `(user_id, asset_type)`
- `market_data`: `UNIQUE (asset_id, date)` `(date)`
- `rankings`: `(date, change_rate)` `(user_id, date)` `(asset_id, date)` `(date)`

---

## 📡 API 速查

后端 base URL：`https://sweep-the-board-production.up.railway.app`
前端代理路径：`https://sweep-the-board.vercel.app/api/...`

| 路径 | 方法 | 用途 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/users` | GET / POST | 用户列表 / 创建用户 |
| `/api/users/{id}` | GET / PUT / DELETE | 用户 CRUD |
| `/api/users/{id}/avatar` | POST | 上传头像（multipart，≤5MB） |
| `/api/assets` | GET / POST | 资产列表 / 创建资产 |
| `/api/assets/{id}` | GET / PUT / DELETE | 资产 CRUD |
| `/api/data/snapshot` | GET | 资产快照（含涨跌幅、稳健度） |
| `/api/data/update` | POST | 手动触发数据更新（返回 task_id） |
| `/api/data/task/{task_id}` | GET | 查询更新任务状态 |
| `/api/data/charts/all` | GET | 所有资产收益曲线 |
| `/api/data/charts/weekly` | GET | 周度图表 |
| `/api/data/assets/{id}` | GET | 单个资产历史行情 |
| `/api/ranking` | GET | 综合排行榜（资产 + 用户） |
| `/api/ranking/weekly` | GET | 周度 TOP5 |
| `/api/ranking/users/{user_id}` | GET | 单用户排名历史 |
| `/api/pk-pools` | GET / POST | PK 池列表 / 创建 |
| `/api/pk-pools/{id}/detail` | GET | PK 池详情（含图表） |

完整 API 文档：<https://sweep-the-board-production.up.railway.app/docs>

---

## 🛡️ 稳定性设计

### 行情拉取容错

`services/_resilience.py` 提供 `with_retry` 装饰器，给所有外部数据源调用加了：

- **3 次指数退避重试**（首次失败后 2s → 4s → 10s 重试）
- **单次 30s 超时**（用 ThreadPoolExecutor 包裹同步调用，强制取消）
- **统一异常类型** `ExternalAPIError`，方便上层捕获

涉及的外部调用：
- `_ak_stock_zh_a_hist` / `_ak_futures_zh_daily_sina` / `_ak_fund_etf_hist_sina`
- `_yf_ticker_history`
- `_bs_query_history_k_data_plus`

### 定时任务

`services/scheduler.py` 用 APScheduler 在 FastAPI lifespan 中挂载：

| 任务 | Cron | 用途 |
|------|------|------|
| 行情主更新 | 工作日 16:00（Asia/Shanghai） | A 股收盘后拉取所有资产 |
| 行情兜底更新 | 工作日 22:30 | 美股开盘前补漏 |
| 心跳健康自检 | 每天 03:00 | 日志确认 scheduler 还活着 |

通过环境变量 `SCHEDULER_ENABLED=true` 启用（本地默认关闭，避免频繁打外部 API）。

### 前端 SWR 缓存

`lib/hooks.ts` 封装了所有 SWR hooks：

- 30 秒内同 key 自动去重
- 窗口聚焦时后台 revalidate
- 失败自动重试 3 次（指数退避）
- 数据更新后调用 `invalidateAfterDataUpdate()` 让所有相关缓存过期

---

## 📅 数据配置

- **基准日期**：2026 年 1 月 5 日
- **追踪窗口**：2026-01-05 ~ 2026-12-31
- **涨跌幅计算**：`(最新价 - 基准价) / 基准价 × 100%`
- **排名规则**：每个用户取自己核心资产的累计涨跌幅，全员相对排名

---

## 🐛 已知问题与排坑记录

迁移到 Vercel + Railway 过程中遇到的坑（避免后来人踩同样的坑）：

| 现象 | 根因 | 解决方案 |
|------|------|---------|
| Railway 启动崩溃 `TypeError: __firstlineno__` | Python 3.13 默认 + SQLAlchemy 2.0.30 不兼容 | 加 `backend/.python-version` 内容 `3.11` |
| 数据库连接 `Network is unreachable (IPv6)` | Railway 免费套餐不支持 IPv6，Supabase 直连解析为 IPv6 | 改用 Transaction Pooler 域名（IPv4） |
| `FATAL: no tenant identifier provided` | Pooler 需要多租户标识 | 用户名改为 `postgres.<project-ref>` |
| 涨跌色徽章不显示 / 颜色错乱 | Tailwind 默认 `content` 不扫 `lib/` 目录 | 在 `tailwind.config.ts` 加 `./lib/**/*.{ts,tsx}` + safelist |

---

## 📝 版本历史

### v1.1.0（2026-05）— 部署架构迁移 + 性能优化

**部署架构**：
- 🚀 从 HuggingFace Spaces 迁移到 **Vercel + Railway + Supabase** 三平台
- ⚡ 前端走 Vercel CDN，告别冷启动
- 🐍 后端固定 Python 3.11，Supabase Pooler IPv4 连接

**视觉升级**：
- 🥇 龙虎榜金银铜奖牌徽章 + 涨跌热力色（4 档强度）
- 🦴 统一 Skeleton 骨架屏替代"加载中..."
- 🎨 颜色编码统一为 A 股惯例红涨绿跌 + ↑/↓ 箭头辅助
- 🔍 SEO 元数据完善（OG / Twitter Card / sitemap.xml / robots.txt）

**性能稳定性**：
- 💾 引入 SWR 客户端缓存，消除组件重复请求
- 🛡️ 行情拉取自带 3 次重试 + 30s 超时（tenacity）
- 🤖 APScheduler 定时任务（工作日 16:00 / 22:30 自动更新）
- ⚡ 数据库索引补齐（assets / market_data / rankings 共 9 个索引）
- 📋 结构化日志替代 print

### v1.0.0（2026-01-11）— 首版发布

- 用户和资产管理（CRUD）
- 排行榜（资产排名 + 用户排名）
- 数据可视化（Recharts）
- 管理后台（用户、资产、数据更新）
- 头像上传（≤5MB，JPG/PNG/WebP）
- 多市场支持（股票、基金、期货）
- 一人多资产
- 响应式设计

---

## 📚 相关文档

- [部署文档](./sweep-the-board-deployment.md)（如有） — 详细的部署配置记录
- [本地运行指南](./LOCAL_RUN_GUIDE.md)
- [Hugging Face 部署存档](./README_HF.md)（已废弃，保留参考）

---

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提 Issue 和 PR！

---

🤖 *Sections of this README were generated with assistance from [Claude](https://claude.com/claude-code).*
