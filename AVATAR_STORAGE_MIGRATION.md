# 头像存储迁移到 Supabase Storage

## 迁移完成

头像存储已成功从本地文件系统迁移到 Supabase Storage。所有新上传的头像将直接存储到 Supabase Storage，确保代码推送后头像不会丢失。

## 环境变量配置

### 需要在 Hugging Face Spaces Secrets 中添加

1. **SUPABASE_URL**（必需）
   - 格式：`https://{project-ref}.supabase.co`
   - 获取位置：Supabase 项目设置 > API > Project URL
   - 用途：用于初始化 Supabase 客户端和生成公网 URL

2. **SUPABASE_SERVICE_ROLE_KEY**（必需）
   - 格式：Supabase 项目的 Service Role Key（长字符串）
   - 获取位置：Supabase 项目设置 > API > service_role key（secret）
   - 用途：用于 Supabase Storage 的写入权限
   - **重要**：Service Role Key 具有完整权限，请妥善保管，不要泄露

### 配置步骤

1. 登录 Hugging Face Spaces
2. 进入你的 Space 设置
3. 找到 "Secrets" 或 "Environment variables" 部分
4. 添加以下两个环境变量：
   - `SUPABASE_URL` = `https://your-project.supabase.co`
   - `SUPABASE_SERVICE_ROLE_KEY` = `your-service-role-key`

## Supabase Storage 设置

### 创建 avatars Bucket

1. 登录 Supabase 控制台
2. 进入 Storage 页面
3. 点击 "Create a new bucket"
4. 设置：
   - **Bucket name**: `avatars`
   - **Public bucket**: ✅ 勾选（允许公网访问）
5. 点击 "Create bucket"

### Bucket 权限设置

确保 `avatars` bucket 设置为公开（Public），这样头像 URL 才能被公网访问。

## 代码变更

### 新增文件
- `backend/services/storage.py` - Supabase Storage 服务模块

### 修改文件
- `backend/requirements.txt` - 添加 `supabase>=2.0.0` 依赖
- `backend/config.py` - 添加 Supabase 配置变量
- `backend/services/__init__.py` - 导出 storage 模块
- `backend/api/routes.py` - 修改头像上传接口使用 Supabase Storage

### 功能说明

- **上传头像**：新上传的头像直接存储到 Supabase Storage
- **删除旧头像**：替换头像时自动删除 Supabase Storage 中的旧文件
- **公网 URL**：数据库存储完整的 Supabase Storage 公网 URL
- **向后兼容**：旧的本地路径头像仍然可以显示（如果静态文件服务仍启用）

## 数据迁移

### 现有头像处理

如果数据库中已有头像 URL（格式为 `/avatars/{file_name}`），这些是旧的本地路径：

- **选项1**：保留静态文件服务，旧头像仍可访问
- **选项2**：手动迁移旧头像到 Supabase Storage（需要编写迁移脚本）
- **选项3**：用户重新上传头像时自动迁移到 Supabase Storage

### 新上传头像

迁移后所有新上传的头像都会：
- 直接存储到 Supabase Storage
- 数据库存储完整的公网 URL（格式：`https://{project}.supabase.co/storage/v1/object/public/avatars/{file_name}`）

## 测试验证

部署后请测试：

1. ✅ 上传新头像：验证文件成功上传到 Supabase Storage
2. ✅ 数据库记录：验证 `avatar_url` 存储的是完整的 Supabase Storage 公网 URL
3. ✅ 公网访问：验证头像 URL 可以在浏览器中直接访问
4. ✅ 删除旧头像：验证替换头像时旧文件被正确删除
5. ✅ 错误处理：测试各种异常情况（文件过大、格式不支持、Supabase 连接失败等）

## 故障排查

### 上传失败

- 检查 `SUPABASE_URL` 和 `SUPABASE_SERVICE_ROLE_KEY` 是否正确配置
- 检查 `avatars` bucket 是否已创建且设置为公开
- 查看后端日志中的错误信息

### 头像无法显示

- 检查头像 URL 是否为完整的 Supabase Storage 公网 URL
- 检查 bucket 是否设置为公开
- 检查文件是否成功上传到 Supabase Storage

## 注意事项

1. **Service Role Key 安全**：Service Role Key 具有完整权限，请妥善保管，不要提交到代码仓库
2. **Bucket 公开性**：`avatars` bucket 必须设置为公开，否则头像无法被公网访问
3. **文件大小限制**：仍然保持 5MB 的文件大小限制
4. **支持格式**：支持 JPG、JPEG、PNG、WebP 格式
