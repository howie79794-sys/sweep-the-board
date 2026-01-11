# CoolDown龙虎榜

一个可扩展的金融资产排行榜网站，支持多用户、多资产、多市场类型，记录各种金融资产的每日数据，支持排名展示、数据可视化。

## 项目特性

- 📊 支持多种资产类型：股票、基金、期货、外汇等
- 👥 支持多用户管理，每人可选择多支资产
- 📈 基于涨跌幅的排名系统（相对于2026-01-05基准日）
- 🏆 第一名荣誉标签展示
- 📱 响应式设计，支持移动端
- 🔄 手动和自动数据更新
- 🎨 现代化的UI设计
- 🔒 数据持久化，更新部署不影响用户数据

## 技术栈

- **前端**: Next.js 14 (App Router), Tailwind CSS, shadcn/ui, Recharts
- **后端**: FastAPI (Python)
- **数据库**: SQLite
- **数据源**: akshare
- **部署**: Hugging Face Spaces + GitHub Actions

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 20+
- npm 或 yarn

### 安装和运行

#### 1. 克隆项目

```bash
git clone <repository-url>
cd cool-down-leaderboard
```

#### 2. 后端设置

```bash
cd backend
pip install -r requirements.txt
python3 -m database.init_db
PYTHONPATH=. uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. 前端设置

```bash
cd frontend
npm install
npm run dev
```

#### 4. 访问应用

- 前端界面: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

## 项目结构

```
cool-down-leaderboard/
├── frontend/          # Next.js前端
│   ├── app/          # 页面
│   ├── components/   # 组件
│   └── lib/          # 工具函数
├── backend/          # Python后端
│   ├── api/          # API路由
│   ├── models/       # 数据模型
│   ├── services/     # 业务逻辑
│   └── database/     # 数据库
├── data/             # 数据存储（不提交到Git）
│   ├── database.db   # 数据库文件
│   └── avatars/      # 用户头像
├── .github/          # GitHub Actions
└── README.md
```

## 数据持久化

### 重要说明

- **用户数据不会被 Git 跟踪**: `data/database.db` 和 `data/avatars/` 已添加到 `.gitignore`
- **无感更新部署**: 每次代码更新不会覆盖用户编辑的个人信息和上传的头像
- **数据备份**: 建议定期备份 `data/` 目录

## 初始数据

- **基准日期**: 2026年1月5日
- **数据追踪**: 2026年1月6日 - 2026年12月31日
- **初始资产**: 8支A股股票/ETF

## 功能说明

### 排行榜

- 资产排名：按涨跌幅对资产进行排名
- 用户排名：按用户最佳资产涨跌幅进行排名
- 荣誉标签：第一名特殊展示

### 管理界面

- 用户管理：添加、编辑、删除用户，上传头像
- 资产管理：添加、编辑、删除资产
- 数据管理：触发数据更新

## 部署

### GitHub 设置

详见 [GITHUB_SETUP.md](./GITHUB_SETUP.md)

### Hugging Face Spaces

详见 [README_HF.md](./README_HF.md) 和 [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)

### GitHub Actions

配置了基本的GitHub Actions工作流，需要设置以下Secrets：

- `HF_TOKEN`: Hugging Face访问令牌
- `HF_USERNAME`: Hugging Face用户名
- `HF_SPACE`: Space名称（可选）

## 开发

### 代码结构

- 前端组件位于 `frontend/components/`
- 后端API路由位于 `backend/api/routes/`
- 数据模型位于 `backend/models/`
- 业务逻辑位于 `backend/services/`

### 数据更新

数据更新可以通过以下方式：

1. 管理界面：访问 `/admin` 页面，点击"更新所有资产数据"
2. API调用：`POST /api/data/update`
3. GitHub Actions：配置定时任务自动更新

## 版本历史

- **v1.0.0** (2026-01-11): 首个版本发布
  - 完整的用户和资产管理功能
  - 排行榜展示
  - 数据可视化
  - 管理界面

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 相关文档

- [部署指南](./DEPLOYMENT_GUIDE.md) - 无感更新部署说明
- [GitHub设置](./GITHUB_SETUP.md) - GitHub仓库设置指南
- [服务启动](./README_SERVICES.md) - 本地开发服务启动说明
