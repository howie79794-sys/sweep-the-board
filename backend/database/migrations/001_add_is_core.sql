-- 资产分级功能：添加 is_core 字段
-- 迁移日期：2026-01-19
-- 描述：在 assets 表中新增 is_core 字段，用于标识核心资产

-- 添加 is_core 字段（布尔类型，默认值为 False）
ALTER TABLE assets ADD COLUMN is_core BOOLEAN DEFAULT 0 NOT NULL;

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_assets_is_core ON assets(is_core);

-- 验证迁移
-- 执行完成后，可以运行以下查询来验证字段已添加：
-- SELECT * FROM pragma_table_info('assets') WHERE name = 'is_core';
