# 资产分级功能迁移指南

## 概述

本次更新实现了资产分级逻辑，新增了"核心资产"概念，遵循"一用户一心"原则：每个用户只能有一个核心资产。

## 功能特性

1. **数据库变更**：
   - 在 `assets` 表中新增 `is_core` 字段（布尔类型，默认值为 `False`）

2. **数据迁移**：
   - 将所有现有资产标记为核心资产
   - 如果同一用户有多个资产，仅保留 ID 最小（最早创建）的为核心资产

3. **后端约束**：
   - 创建资产时，如果设置 `is_core=True`，会校验该用户是否已有核心资产
   - 更新资产时，如果设置 `is_core=True`，会校验该用户是否已有其他核心资产

4. **前端展示**：
   - 资产卡片上显示醒目的"核心"徽章
   - 管理界面资产列表中显示核心徽章
   - 编辑弹窗中增加"设置为核心资产"复选框

## 迁移步骤

### 第一步：备份数据库

```bash
# 如果使用 SQLite
cp data/yqt.db data/yqt.db.backup-$(date +%Y%m%d)

# 如果使用 PostgreSQL
pg_dump your_database > backup-$(date +%Y%m%d).sql
```

### 第二步：执行数据库结构迁移

#### 方法 1：手动执行 SQL（推荐用于生产环境）

```bash
# 进入项目目录
cd /path/to/yqt

# 执行迁移 SQL
sqlite3 data/yqt.db < backend/database/migrations/001_add_is_core.sql

# 或者使用 psql（如果是 PostgreSQL）
psql your_database < backend/database/migrations/001_add_is_core.sql
```

#### 方法 2：使用 SQLAlchemy 自动创建（开发环境）

```bash
# 设置环境变量
export DATABASE_URL='your_database_url'

# 删除数据库（⚠️ 仅用于开发环境！会丢失所有数据）
rm data/yqt.db

# 重新初始化数据库
cd backend
python database/init_db.py
```

### 第三步：执行数据迁移脚本

```bash
# 设置环境变量（如果尚未设置）
export DATABASE_URL='your_database_url'

# 执行迁移脚本
cd backend
python scripts/migrate_is_core.py
```

脚本执行过程中会提示：
```
⚠️  此脚本将修改数据库中的资产数据
操作内容：
  1. 将所有现有资产标记为核心资产 (is_core=True)
  2. 如果同一用户有多个资产，仅保留 ID 最小的为核心资产
  3. 其余资产设置为非核心资产 (is_core=False)

确认继续？(yes/no):
```

输入 `yes` 确认执行。

### 第四步：验证迁移结果

1. **检查数据库**：
```bash
# SQLite
sqlite3 data/yqt.db "SELECT user_id, COUNT(*) as core_count FROM assets WHERE is_core = 1 GROUP BY user_id;"

# PostgreSQL
psql your_database -c "SELECT user_id, COUNT(*) as core_count FROM assets WHERE is_core = true GROUP BY user_id;"
```

预期结果：每个用户的 `core_count` 应该为 1。

2. **检查 Web 界面**：
   - 访问管理界面 `/admin`
   - 查看资产列表，应该看到核心资产显示"核心"徽章
   - 编辑资产，应该看到"设置为核心资产"复选框

### 第五步：重启服务

```bash
# 重启后端服务
cd backend
./start_backend.sh

# 重启前端服务
cd frontend
npm run dev
```

## 回滚步骤

如果迁移出现问题，可以回滚：

1. **恢复数据库备份**：
```bash
# SQLite
cp data/yqt.db.backup-YYYYMMDD data/yqt.db

# PostgreSQL
psql your_database < backup-YYYYMMDD.sql
```

2. **回滚代码**：
```bash
git checkout HEAD~1  # 回退到上一个版本
```

## 注意事项

1. **生产环境迁移**：
   - 务必先备份数据库
   - 建议在非高峰时段执行迁移
   - 先在测试环境验证迁移脚本

2. **数据一致性**：
   - 迁移脚本会自动处理多资产用户，无需手动干预
   - 如果有特殊需求（如指定某个资产为核心），可以在迁移后通过管理界面手动调整

3. **API 兼容性**：
   - 新增的 `is_core` 字段在 API 响应中会自动返回
   - 旧的前端代码可能无法显示核心徽章，需要更新前端代码

## 常见问题

**Q: 迁移脚本报错 "DATABASE_URL 环境变量未设置"？**

A: 需要设置 `DATABASE_URL` 环境变量，例如：
```bash
export DATABASE_URL='sqlite:///data/yqt.db'
```

**Q: 迁移后发现某个用户有多个核心资产？**

A: 这不应该发生，请检查迁移脚本是否正确执行。可以运行验证 SQL：
```sql
SELECT user_id, COUNT(*) as core_count FROM assets WHERE is_core = 1 GROUP BY user_id HAVING core_count > 1;
```

**Q: 如何手动调整核心资产？**

A: 通过管理界面 `/admin`：
1. 找到要设置为核心的资产，点击"编辑"
2. 勾选"设置为核心资产"
3. 如果该用户已有核心资产，系统会提示先取消原有核心设置

## 相关文件

- 数据库模型：`backend/database/models.py`
- 迁移脚本：`backend/scripts/migrate_is_core.py`
- SQL 迁移：`backend/database/migrations/001_add_is_core.sql`
- API 路由：`backend/api/routes.py`
- 前端类型：`frontend/types/index.ts`
- 前端组件：`frontend/components/AssetCard.tsx`
- 管理界面：`frontend/app/admin/page.tsx`
