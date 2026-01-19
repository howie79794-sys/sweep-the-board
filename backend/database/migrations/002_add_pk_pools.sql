-- 自定义 PK 池功能：添加 pk_pools 和 pk_pool_assets 表
-- 迁移日期：2026-01-19
-- 描述：支持 PK 池及资产多对多关联

-- PK 池表
CREATE TABLE IF NOT EXISTS pk_pools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- PK 池与资产关联表
CREATE TABLE IF NOT EXISTS pk_pool_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pool_id INTEGER NOT NULL,
    asset_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pool_id) REFERENCES pk_pools(id) ON DELETE CASCADE,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
    UNIQUE(pool_id, asset_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_pk_pools_name ON pk_pools(name);
CREATE INDEX IF NOT EXISTS idx_pk_pool_assets_pool_id ON pk_pool_assets(pool_id);
CREATE INDEX IF NOT EXISTS idx_pk_pool_assets_asset_id ON pk_pool_assets(asset_id);
