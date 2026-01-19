<!-- ASCII-only document -->
# 自定义 PK 池部署说明

本说明覆盖 Hugging Face 部署与数据库迁移的一键流程。

## 启动流程已包含的迁移逻辑

当前 `start.sh` 启动流程会调用：

```
python3 -m database.init_db
```

`init_db` 会执行 SQLAlchemy `Base.metadata.create_all`，因此 **新表 `pk_pools` 和 `pk_pool_assets` 会在启动时自动创建**。
这满足 Hugging Face 容器的自动部署需求。

## 需要手动执行的场景

如果你使用的是 **已有数据库**（尤其是 SQLite 或已有生产库），建议手动执行迁移脚本，以确保表结构完整：

```
sqlite3 data/yqt.db < backend/database/migrations/002_add_pk_pools.sql
sqlite3 data/yqt.db < backend/database/migrations/003_add_pk_pool_date_range.sql
```

如果是 PostgreSQL，请用 `psql` 执行同名 SQL。

## 一键部署建议

在 Hugging Face 上：

1. 设置 `DATABASE_URL` 环境变量
2. 直接运行 `start.sh`

这将自动完成：
- 创建新表
- 启动后端 API
- 启动前端 UI

## 验证

部署完成后访问：

- `/pk-pools` 页面可以创建和管理 PK 池
- `/pk-pools/{id}` 页面可查看池内曲线与明细表

## 迁移文件

- `backend/database/migrations/002_add_pk_pools.sql`

