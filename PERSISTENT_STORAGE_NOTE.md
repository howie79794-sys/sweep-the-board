# 数据库持久化配置说明

## Hugging Face Spaces Persistent Storage 配置

**重要提示**: 在 Hugging Face Spaces 部署时，必须开启 Persistent Storage 以确保数据持久化。

### 配置步骤

1. 在 Hugging Face Spaces 项目中，进入 **Settings** 页面
2. 找到 **Storage** 或 **Persistent Storage** 选项
3. 开启 Persistent Storage
4. 配置挂载路径: `/app/data`

### 数据库位置

- **数据库文件**: `/app/data/database.db`
- **头像文件**: `/app/data/avatars/`

### 验证持久化

部署后，可以通过以下方式验证：

1. 添加一些数据（用户、资产）
2. 重新部署项目
3. 检查数据是否仍然存在

### 注意事项

- 如果不开启 Persistent Storage，每次部署都会丢失所有数据
- Persistent Storage 有存储限制，请查看 Hugging Face 的配额
- 定期备份数据库文件到 Git（如果需要）