# 市场数据重构部署步骤

## 1. 安装依赖

首先安装新增的 AkShare 库：

```bash
cd /Users/zhuangjiaxuan/.cursor/worktrees/sweep_the_board/ngi
pip install -r backend/requirements.txt
```

或者单独安装：

```bash
pip install akshare>=1.16.0
```

## 2. 本地测试

运行测试脚本验证功能：

```bash
cd /Users/zhuangjiaxuan/.cursor/worktrees/sweep_the_board/ngi
export PYTHONPATH=$PYTHONPATH:$(pwd)/backend
python3 backend/scripts/test_market_data.py
```

预期输出：
- ✓ 数据源可用性检查通过
- ✓ A股数据获取成功
- ✓ 期货数据获取成功（如果测试）
- ✓ 美股数据获取成功（如果测试）

## 3. 启动服务

### 方法1：使用现有启动脚本

```bash
cd /Users/zhuangjiaxuan/.cursor/worktrees/sweep_the_board/ngi
export DATABASE_URL="your-database-url"
python3 app.py
```

### 方法2：直接启动后端

```bash
cd /Users/zhuangjiaxuan/.cursor/worktrees/sweep_the_board/ngi
export DATABASE_URL="your-database-url"
export PYTHONPATH=$PYTHONPATH:$(pwd)/backend
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

## 4. 验证运行状态

### 检查日志

启动后查看日志，应该看到：
```
[市场数据] akshare 已加载
```

### 测试 API 端点

```bash
# 获取资产列表
curl http://localhost:8000/api/assets

# 更新特定资产数据（观察路由日志）
curl -X POST http://localhost:8000/api/data/update/1
```

## 5. 观察路由行为

在日志中查看分流路由的工作情况：

```
[市场数据] [路由] 识别为A股，优先使用 AkShare
[市场数据] [akshare] 成功获取 5 条数据
```

或者如果遇到频率限制：

```
[市场数据] [路由] ⚠️ yfinance 触发频率限制
[市场数据] [路由] 自动降级到 baostock
```

## 6. 部署到生产环境

### 更新 Hugging Face Space（如果使用）

1. 确保根目录的 `requirements.txt` 包含 akshare：
   ```txt
   akshare>=1.16.0
   ```

2. 提交更改：
   ```bash
   git add .
   git commit -m "重构: 实现 yfinance + AkShare 混合路由"
   git push
   ```

3. Hugging Face Space 会自动重新部署

### Docker 部署（如果使用）

更新 Dockerfile，确保安装 akshare：

```dockerfile
RUN pip install -r backend/requirements.txt
```

重新构建镜像：

```bash
docker build -t market-data-service .
docker run -p 8000:8000 market-data-service
```

## 7. 常见问题排查

### AkShare 导入失败

```bash
pip install --upgrade akshare
```

### 期货数据获取失败

AkShare 期货接口可能因版本而异，检查版本：

```bash
pip show akshare
```

如果版本过旧，升级到最新版：

```bash
pip install --upgrade akshare
```

### 日期格式错误

确保所有日期输入都是 `YYYY-MM-DD` 格式。如果遇到错误，检查日志中的日期格式化信息。

### 频率限制

如果频繁触发 yfinance 频率限制，系统会自动降级到 AkShare 或 Baostock。观察日志中的降级信息。

## 8. 监控建议

### 关键指标

- 数据源切换频率（通过日志统计）
- API 调用成功率
- 数据获取延迟
- 频率限制触发次数

### 日志关键字

监控以下日志关键字：

- `[路由]` - 路由决策
- `⚠️` - 警告和降级
- `✓ 成功获取` - 成功
- `✗` - 失败

## 9. 回滚方案

如果需要回滚到之前的版本：

```bash
# 1. 回退到上一个提交
git revert HEAD

# 2. 或者直接检出之前的版本
git checkout <previous-commit-hash>

# 3. 重启服务
python3 app.py
```

## 10. 下一步优化

- [ ] 添加 AkShare 财务指标接口
- [ ] 实现数据源健康检查
- [ ] 添加性能监控仪表板
- [ ] 优化缓存策略

---

## 技术支持

如有问题，请查看以下文档：

1. `MARKET_DATA_REFACTOR_SUMMARY.md` - 重构详细说明
2. 日志文件 - 查看实时运行状态
3. 测试脚本 - `backend/scripts/test_market_data.py`
