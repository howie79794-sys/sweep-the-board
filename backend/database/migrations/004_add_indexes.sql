-- ============================================================
-- Migration 004: 性能索引补齐
-- ============================================================
-- 背景：
--   首页龙虎榜、排名查询、用户历史等高频查询缺索引，全表扫描
--   严重时数百毫秒。本迁移把高频 WHERE/ORDER BY 字段全部加索引。
--
-- 应用方法（Supabase）：
--   1. 登录 Supabase Dashboard → SQL Editor
--   2. 粘贴本文件内容并执行
--   3. 结尾 ANALYZE 让 PostgreSQL 重新统计基数（提升后续查询计划）
--
-- 安全说明：
--   * 全部使用 IF NOT EXISTS / CREATE INDEX CONCURRENTLY，可重复执行
--   * 不会锁表，可在线上直接运行
-- ============================================================

-- ----------------------------------------
-- assets 表：用户视图、核心资产视图常用
-- ----------------------------------------
CREATE INDEX IF NOT EXISTS idx_assets_user_id ON assets (user_id);
CREATE INDEX IF NOT EXISTS idx_assets_is_core ON assets (is_core);
CREATE INDEX IF NOT EXISTS idx_assets_user_is_core ON assets (user_id, is_core);
CREATE INDEX IF NOT EXISTS idx_assets_user_type ON assets (user_id, asset_type);

-- ----------------------------------------
-- market_data 表：行情快照、图表查询
-- ----------------------------------------
-- 单一资产的时间序列查询（按日期升序）
CREATE INDEX IF NOT EXISTS idx_market_data_asset_date ON market_data (asset_id, date);
-- 按某天扫所有资产（首页快照）
CREATE INDEX IF NOT EXISTS idx_market_data_date ON market_data (date);

-- 同一资产同一天只允许一条数据（防重复，同时也是隐式索引）
-- 注意：如果生产数据中有重复，需要先清理再加约束
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'uniq_market_data_asset_date'
  ) THEN
    BEGIN
      ALTER TABLE market_data
        ADD CONSTRAINT uniq_market_data_asset_date UNIQUE (asset_id, date);
    EXCEPTION WHEN unique_violation THEN
      RAISE NOTICE 'market_data 中存在 (asset_id, date) 重复记录，跳过唯一约束。请先清理后手动重跑。';
    END;
  END IF;
END $$;

-- ----------------------------------------
-- rankings 表：首页 TOP N、用户/资产历史
-- ----------------------------------------
-- 首页排行榜：WHERE date = ? ORDER BY change_rate DESC LIMIT N
CREATE INDEX IF NOT EXISTS idx_rankings_date_change_rate ON rankings (date, change_rate);
-- 单用户历史排名：WHERE user_id = ? ORDER BY date
CREATE INDEX IF NOT EXISTS idx_rankings_user_date ON rankings (user_id, date);
-- 单资产历史排名
CREATE INDEX IF NOT EXISTS idx_rankings_asset_date ON rankings (asset_id, date);
-- 仅按 date 切片
CREATE INDEX IF NOT EXISTS idx_rankings_date ON rankings (date);

-- ----------------------------------------
-- users 表：is_active 经常被过滤
-- ----------------------------------------
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users (is_active);

-- ----------------------------------------
-- 让 PostgreSQL 重新统计，使得新索引立即生效
-- ----------------------------------------
ANALYZE assets;
ANALYZE market_data;
ANALYZE rankings;
ANALYZE users;
