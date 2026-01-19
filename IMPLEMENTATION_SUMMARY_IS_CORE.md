# 资产分级功能实施完成总结

## 项目概述

本次更新全栈实现了资产分级逻辑，引入"核心资产"概念，遵循"一用户一心"原则：每个用户只能有一个核心资产。

实施日期：2026-01-19

## 实施内容

### 第一阶段：数据库变更与历史数据迁移

#### 1. 数据库模型修改

**文件**：`backend/database/models.py`

**变更**：
- 在 `Asset` 模型中新增 `is_core` 字段（布尔类型，默认值为 `False`）

```python
is_core = Column(Boolean, default=False, nullable=False)  # 是否为核心资产（一用户一心）
```

#### 2. 数据库 Schema 更新

**文件**：`backend/database/schema.sql`

**变更**：
- 在 `assets` 表定义中添加 `is_core` 字段
- 新增索引 `idx_assets_is_core` 提高查询性能

#### 3. 数据迁移脚本

**文件**：`backend/scripts/migrate_is_core.py`

**功能**：
- 扫描所有现有资产
- 将所有资产的 `is_core` 设为 `True`
- 如果同一用户有多个资产，仅将 ID 最小（最早创建）的设为 `True`，其余设为 `False`
- 自动验证迁移结果

**执行方式**：
```bash
export DATABASE_URL='your_database_url'
cd backend
python scripts/migrate_is_core.py
```

#### 4. SQL 迁移文件

**文件**：`backend/database/migrations/001_add_is_core.sql`

**内容**：
- 添加 `is_core` 字段的 SQL 语句
- 创建索引的 SQL 语句

**执行方式**：
```bash
sqlite3 data/yqt.db < backend/database/migrations/001_add_is_core.sql
```

### 第二阶段：后端 API 升级

#### 1. Pydantic 模型更新

**文件**：`backend/api/routes.py`

**变更**：

- **AssetCreate**：新增 `is_core` 字段（可选，默认 `False`）
- **AssetUpdate**：新增 `is_core` 字段（可选）
- **AssetResponse**：新增 `is_core` 字段（必填）

#### 2. 资产创建接口增强

**接口**：`POST /assets`

**新增逻辑**：
- 校验：如果要设置 `is_core=True`，确保该用户没有其他核心资产
- 错误提示："该用户已有关联的核心资产，请先取消原核心设置"

#### 3. 资产更新接口增强

**接口**：`PUT /assets/{asset_id}`

**新增逻辑**：
- 校验：如果要设置 `is_core=True`，确保该用户没有其他核心资产（排除当前资产）
- 支持跨用户更新时的核心资产校验
- 错误提示："该用户已有关联的核心资产，请先取消原核心设置"

#### 4. 资产查询接口更新

**接口**：`GET /assets`, `GET /assets/{asset_id}`

**变更**：
- 返回数据中包含 `is_core` 字段

### 第三阶段：前端界面升级

#### 1. TypeScript 类型定义

**文件**：`frontend/types/index.ts`

**变更**：
- 在 `Asset` 接口中新增 `is_core: boolean` 字段

#### 2. 资产卡片组件增强

**文件**：`frontend/components/AssetCard.tsx`

**变更**：
- 为核心资产显示醒目的"核心"徽章
- 徽章样式：渐变背景（黄色到橙色），白色文字，圆角

```tsx
{asset.is_core && (
  <span className="text-xs px-2 py-0.5 bg-gradient-to-r from-yellow-400 to-orange-400 text-white font-semibold rounded">
    核心
  </span>
)}
```

#### 3. 管理界面资产列表

**文件**：`frontend/app/admin/page.tsx`

**变更**：
- 在资产列表中显示核心徽章
- 资产名称旁边显示"核心"标签

#### 4. 管理界面编辑弹窗

**文件**：`frontend/app/admin/page.tsx`

**变更**：
- 新增"设置为核心资产"复选框
- 添加提示文本："每个用户只能有一个核心资产。如果该用户已有核心资产，请先取消原有核心设置。"
- 前端表单状态管理：
  - `assetForm` 新增 `is_core` 字段
  - 创建/编辑/更新时传递 `is_core` 值

**用户交互流程**：
1. 点击"编辑"按钮，弹窗显示当前资产的 `is_core` 状态
2. 勾选/取消勾选"设置为核心资产"复选框
3. 点击"更新"按钮，提交更新
4. 后端校验：如果该用户已有核心资产，返回错误提示
5. 前端显示错误信息："该用户已有关联的核心资产，请先取消原核心设置"

## 技术细节

### 后端约束逻辑

1. **创建资产时**：
   ```python
   if asset.is_core:
       existing_core = db.query(Asset).filter(
           Asset.user_id == asset.user_id,
           Asset.is_core == True
       ).first()
       if existing_core:
           raise HTTPException(status_code=400, detail="该用户已有关联的核心资产，请先取消原核心设置")
   ```

2. **更新资产时**：
   ```python
   if "is_core" in update_data and update_data["is_core"] == True:
       target_user_id = update_data.get("user_id", db_asset.user_id)
       existing_core = db.query(Asset).filter(
           Asset.user_id == target_user_id,
           Asset.is_core == True,
           Asset.id != asset_id
       ).first()
       if existing_core:
           raise HTTPException(status_code=400, detail="该用户已有关联的核心资产，请先取消原核心设置")
   ```

### 前端样式设计

**核心徽章样式**：
- 背景：渐变（`bg-gradient-to-r from-yellow-400 to-orange-400`）
- 文字：白色（`text-white`）
- 字体：粗体（`font-semibold`）
- 大小：小号（`text-xs`）
- 内边距：`px-2 py-0.5`
- 圆角：`rounded`

## 文件清单

### 新增文件
1. `backend/scripts/migrate_is_core.py` - 数据迁移脚本
2. `backend/database/migrations/001_add_is_core.sql` - SQL 迁移文件
3. `MIGRATION_IS_CORE.md` - 迁移指南
4. `IMPLEMENTATION_SUMMARY_IS_CORE.md` - 实施总结（本文件）

### 修改文件
1. `backend/database/models.py` - 数据库模型
2. `backend/database/schema.sql` - 数据库 Schema
3. `backend/api/routes.py` - API 路由和逻辑
4. `frontend/types/index.ts` - TypeScript 类型定义
5. `frontend/components/AssetCard.tsx` - 资产卡片组件
6. `frontend/app/admin/page.tsx` - 管理界面

## 测试清单

### 后端测试

- [ ] 创建资产时，默认 `is_core=False`
- [ ] 创建资产时，设置 `is_core=True`，成功创建核心资产
- [ ] 创建第二个核心资产时，返回错误："该用户已有关联的核心资产"
- [ ] 更新资产为核心资产时，校验通过
- [ ] 更新资产为核心资产时，如果该用户已有核心资产，返回错误
- [ ] 查询资产时，返回 `is_core` 字段

### 前端测试

- [ ] 资产卡片上显示"核心"徽章
- [ ] 管理界面资产列表显示核心徽章
- [ ] 编辑弹窗中显示"设置为核心资产"复选框
- [ ] 勾选复选框后保存，后端校验通过
- [ ] 勾选复选框后保存，如果该用户已有核心资产，显示错误提示

### 数据迁移测试

- [ ] 执行迁移脚本，所有资产的 `is_core` 字段已添加
- [ ] 执行数据迁移，所有资产的 `is_core` 设为 `True`
- [ ] 如果同一用户有多个资产，仅 ID 最小的为 `True`
- [ ] 验证查询：每个用户只有一个核心资产

## 部署步骤

1. **备份数据库**
   ```bash
   cp data/yqt.db data/yqt.db.backup-$(date +%Y%m%d)
   ```

2. **执行数据库结构迁移**
   ```bash
   sqlite3 data/yqt.db < backend/database/migrations/001_add_is_core.sql
   ```

3. **执行数据迁移脚本**
   ```bash
   export DATABASE_URL='sqlite:///data/yqt.db'
   cd backend
   python scripts/migrate_is_core.py
   ```

4. **验证迁移结果**
   ```bash
   sqlite3 data/yqt.db "SELECT user_id, COUNT(*) as core_count FROM assets WHERE is_core = 1 GROUP BY user_id;"
   ```

5. **重启服务**
   ```bash
   # 重启后端
   cd backend
   ./start_backend.sh
   
   # 重启前端
   cd frontend
   npm run dev
   ```

6. **验证功能**
   - 访问 `/admin`
   - 查看资产列表，确认核心徽章显示
   - 编辑资产，确认复选框显示
   - 测试核心资产切换功能

## 已知限制

1. **每个用户只能有一个资产**：目前系统保持了原有的"每个用户只能绑定一个资产"的约束，因此核心资产功能在当前版本可能显得冗余。但为未来支持"一用户多资产"预留了扩展空间。

2. **历史数据兼容**：如果系统中已有多个用户共享资产的情况，需要手动清理数据。

## 未来扩展

1. **一用户多资产**：
   - 移除 `UNIQUE(user_id)` 约束
   - 允许用户创建多个资产
   - 核心资产用于主要排名和展示
   - 非核心资产用于辅助分析

2. **资产组合**：
   - 基于核心资产和非核心资产构建投资组合
   - 计算组合收益率
   - 展示资产配置图表

3. **核心资产切换历史**：
   - 记录核心资产的切换历史
   - 分析用户的投资策略变化

## 参考文档

- [迁移指南](./MIGRATION_IS_CORE.md)
- [数据库模型](./backend/database/models.py)
- [API 文档](./backend/api/routes.py)

## 联系方式

如有问题，请联系开发团队。
