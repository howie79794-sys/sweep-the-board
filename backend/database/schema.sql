-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    avatar_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- 资产表
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    asset_type TEXT NOT NULL,
    market TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    baseline_price REAL,
    baseline_date DATE DEFAULT '2026-01-05',
    start_date DATE DEFAULT '2026-01-06',
    end_date DATE DEFAULT '2026-12-31',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, code)
);

-- 市场数据表
CREATE TABLE IF NOT EXISTS market_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    date DATE NOT NULL,
    close_price REAL NOT NULL,
    volume REAL,
    turnover_rate REAL,
    pe_ratio REAL,
    market_cap REAL,
    additional_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
    UNIQUE(asset_id, date)
);

-- 排名表
CREATE TABLE IF NOT EXISTS rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    asset_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    asset_rank INTEGER,
    user_rank INTEGER,
    change_rate REAL,
    rank_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(date, asset_id, rank_type)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_assets_user_id ON assets(user_id);
CREATE INDEX IF NOT EXISTS idx_assets_code ON assets(code);
CREATE INDEX IF NOT EXISTS idx_market_data_asset_id ON market_data(asset_id);
CREATE INDEX IF NOT EXISTS idx_market_data_date ON market_data(date);
CREATE INDEX IF NOT EXISTS idx_rankings_date ON rankings(date);
CREATE INDEX IF NOT EXISTS idx_rankings_asset_id ON rankings(asset_id);
CREATE INDEX IF NOT EXISTS idx_rankings_user_id ON rankings(user_id);
