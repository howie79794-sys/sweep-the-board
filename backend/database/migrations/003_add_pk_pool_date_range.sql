-- 自定义 PK 池功能：添加开始/结束时间
-- 迁移日期：2026-01-19
-- 描述：为 pk_pools 增加 start_date 和 end_date 字段

ALTER TABLE pk_pools ADD COLUMN start_date DATE;
ALTER TABLE pk_pools ADD COLUMN end_date DATE;
