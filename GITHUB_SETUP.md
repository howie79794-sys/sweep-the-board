# GitHub 设置指南

## 首次推送到 GitHub

### 1. 创建 GitHub 仓库

1. 登录 GitHub
2. 点击右上角的 "+" 按钮，选择 "New repository"
3. 填写仓库信息：
   - Repository name: `cooldown-leaderboard`（或您喜欢的名称）
   - Description: "CoolDown龙虎榜 - 金融资产排行榜"
   - Visibility: Public 或 Private
   - **不要**勾选 "Initialize this repository with a README"
4. 点击 "Create repository"

### 2. 初始化本地 Git 仓库并推送

```bash
# 在项目根目录执行

# 初始化 Git 仓库（如果还没有）
git init

# 添加远程仓库（替换 YOUR_USERNAME 和 REPO_NAME）
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git

# 添加所有文件（.gitignore 中的文件会被忽略）
git add .

# 提交
git commit -m "Initial commit: CoolDown龙虎榜 v1.0"

# 推送到 GitHub
git branch -M main
git push -u origin main
```

### 3. 验证推送

访问您的 GitHub 仓库页面，确认所有文件都已上传。

**重要**: 确认 `data/database.db` 和 `data/avatars/` 目录中的文件**没有**被提交（这些文件应该在 `.gitignore` 中）。

## 日常更新流程

### 更新代码并推送

```bash
# 1. 查看修改的文件
git status

# 2. 添加修改的文件
git add .

# 3. 提交
git commit -m "更新说明：描述您的更改"

# 4. 推送到 GitHub
git push origin main
```

### 检查列表

在推送前，确保：

- [ ] `data/database.db` 没有被添加到 Git（已忽略）
- [ ] `data/avatars/` 中的用户上传的头像没有被添加（已忽略）
- [ ] `.env` 文件没有被提交（已忽略）
- [ ] 代码更改已完成并测试

## 数据保护说明

### 不会被 Git 跟踪的文件

以下文件和目录已添加到 `.gitignore`，**不会**被提交到 GitHub：

- `data/database.db` - 数据库文件
- `data/avatars/*` - 用户上传的头像（但保留 `data/avatars/.gitkeep`）
- `.env*` - 环境变量文件
- `node_modules/` - Node.js 依赖
- `__pycache__/` - Python 缓存文件
- `.next/` - Next.js 构建文件

### 部署时的数据持久化

- 生产环境的数据存储在持久化存储中
- 代码更新不会覆盖用户数据
- 用户编辑的个人信息和头像会保留

## 版本标签

建议为重要版本创建 Git 标签：

```bash
# 创建标签
git tag -a v1.0.0 -m "第一个版本发布"

# 推送标签到 GitHub
git push origin v1.0.0
```

## GitHub Actions 自动部署

如果配置了 GitHub Actions，代码推送到 `main` 分支会自动触发部署。

需要设置以下 Secrets：
- `HF_TOKEN`: Hugging Face 访问令牌
- `HF_USERNAME`: Hugging Face 用户名
- `HF_SPACE`: Space 名称（可选）

## 注意事项

1. **不要提交敏感数据**: 确保 `.env` 文件已忽略
2. **不要提交用户数据**: 数据库和头像文件已忽略
3. **提交前测试**: 确保代码可以正常运行
4. **编写清晰的提交信息**: 便于追踪更改历史
