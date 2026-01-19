# 市场数据服务重构总结

## 重构日期
2026-01-19

## 重构目标
实现 yfinance 与 AkShare 混合路由，修复日期格式 Bug，优化数据获取策略

---

## 1. 修复日期格式 Bug

### 问题描述
- Baostock 报错因日期格式被错误转换为 `20260103`（缺少分隔符）
- 不同数据源对日期格式的要求不统一

### 解决方案
✅ **新增 `normalize_date_format()` 函数**
- 统一所有数据源的输入输出为 `YYYY-MM-DD` 格式
- 在 `fetch_stock_data()` 开头对输入日期进行标准化

✅ **改进 `format_date_for_baostock()` 函数**
- 专门用于 Baostock API（YYYYMMDD 格式）
- 优先尝试标准格式 `YYYY-MM-DD` 解析
- 添加详细的错误处理和日志

### 影响范围
- `market_data.py`: 新增日期格式化函数
- 所有数据获取函数：确保输入输出日期格式统一

---

## 2. 引入 AkShare 库

### 依赖添加
✅ **更新 `backend/requirements.txt`**
```txt
akshare>=1.16.0
```

✅ **导入和可用性检查**
```python
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
    print("[市场数据] akshare 已加载")
except ImportError:
    AKSHARE_AVAILABLE = False
    print("[市场数据] 警告: akshare 未安装")
```

---

## 3. 实现分流路由逻辑

### 路由策略

#### 🔷 股指期货（CF. 开头）
- **数据源**: AkShare
- **函数**: `fetch_futures_data_akshare()`
- **支持品种**:
  - `CF.IF0` → 沪深300股指期货主力合约
  - `CF.IC0` → 中证500股指期货主力合约
  - `CF.IH0` → 上证50股指期货主力合约
  - `CF.IM0` → 中证1000股指期货主力合约

#### 🔷 A股（SH./SZ. 开头或6位纯数字）
**优先级**:
1. **AkShare** (`fetch_stock_data_akshare()`) - 规避 yfinance 频率限制
2. **yfinance** (`fetch_stock_data_yfinance()`) - 降级方案
3. **Baostock** (`fetch_stock_data_baostock()`) - 最后备份

#### 🔷 美股/全球（US. 开头或其他）
- **数据源**: yfinance
- **函数**: `fetch_stock_data_yfinance()`

---

## 4. 异常降级策略

### RateLimitError 处理

✅ **自动检测频率限制错误**
```python
if 'RateLimitError' in error_type or 'rate limit' in error_msg.lower() or '429' in error_msg:
    print(f"[市场数据] [路由] ⚠️ yfinance 触发频率限制: {error_msg}")
    print(f"[市场数据] [路由] 自动降级到 baostock")
```

✅ **降级流程**
- **A股**: yfinance → baostock → AkShare（如果之前失败）
- **美股**: 记录日志，提示稍后重试（暂无备用数据源）

✅ **日志记录**
- 所有 API 调用都记录详细日志
- 失败时记录异常类型和错误信息
- 不阻塞整个更新流程（单个资产失败不影响其他资产）

---

## 5. 数据格式对齐

### 标准化数据结构

所有数据源返回的 DataFrame 都包含以下列：
```python
expected_cols = [
    'date',           # 日期 (YYYY-MM-DD)
    'open',           # 开盘价
    'close',          # 收盘价
    'high',           # 最高价
    'low',            # 最低价
    'volume',         # 成交量
    'turnover',       # 成交额
    'amplitude',      # 振幅
    'change_pct',     # 涨跌幅
    'change_amount',  # 涨跌额
    'turnover_rate'   # 换手率
]
```

### 财务指标（仅股票）
```python
financial_cols = [
    'pe_ratio',       # 市盈率
    'pb_ratio',       # 市净率
    'market_cap',     # 总市值（亿元）
    'eps_forecast'    # EPS预测
]
```

### 前端兼容性

✅ **与 `CumulativeReturnChart` 组件兼容**
- 数据格式: `{ date: string, close_price: number, change_rate: number }`
- 日期格式: `YYYY-MM-DD` (ISO 8601)
- 所有数值字段: `number` 类型

---

## 6. 新增函数列表

### 日期处理
- ✅ `normalize_date_format()` - 标准化日期为 YYYY-MM-DD 格式

### 代码转换
- ✅ `convert_akshare_symbol()` - 转换股票代码为 AkShare 格式

### 数据获取
- ✅ `fetch_stock_data_akshare()` - 使用 AkShare 获取A股数据
- ✅ `fetch_futures_data_akshare()` - 使用 AkShare 获取股指期货数据

### 主路由函数（已重构）
- 🔄 `fetch_stock_data()` - 实现混合路由逻辑

---

## 7. 测试建议

### 测试用例

#### A股测试
```python
# 测试上海市场
fetch_stock_data("SH.600519", "2026-01-01", "2026-01-19")  # 贵州茅台
fetch_stock_data("601727", "2026-01-01", "2026-01-19")     # 格式兼容性

# 测试深圳市场
fetch_stock_data("SZ.000001", "2026-01-01", "2026-01-19")  # 平安银行
fetch_stock_data("300857", "2026-01-01", "2026-01-19")     # 格式兼容性
```

#### 股指期货测试
```python
fetch_stock_data("CF.IF0", "2026-01-01", "2026-01-19")   # 沪深300
fetch_stock_data("CF.IC0", "2026-01-01", "2026-01-19")   # 中证500
fetch_stock_data("CF.IH0", "2026-01-01", "2026-01-19")   # 上证50
```

#### 美股测试
```python
fetch_stock_data("US.AAPL", "2026-01-01", "2026-01-19")  # 苹果
fetch_stock_data("AAPL", "2026-01-01", "2026-01-19")     # 格式兼容性
```

#### 频率限制测试
```python
# 连续请求多个资产，观察降级策略
for code in ["600519", "000001", "300857", ...]:
    fetch_stock_data(f"SH.{code}", "2026-01-01", "2026-01-19")
```

---

## 8. 注意事项

### AkShare API 限制
- 部分接口可能需要特定版本的 AkShare
- 期货数据接口名称可能因版本而异
- 建议定期更新 AkShare 到最新版本

### 日期格式要求
- **标准输入输出**: `YYYY-MM-DD`
- **Baostock**: `YYYYMMDD` (在函数内部转换)
- **AkShare**: `YYYYMMDD` (在函数内部转换)
- **yfinance**: `YYYY-MM-DD`

### 错误处理
- 所有函数都有详细的异常处理和日志记录
- 单个数据源失败不影响其他数据源尝试
- 批量更新时单个资产失败不影响其他资产

---

## 9. 性能优化

### 降低频率限制风险
- ✅ A股优先使用 AkShare（免费且无限制）
- ✅ 批量更新时在资产之间添加随机延迟（1-3秒）
- ✅ 自动降级策略避免重复请求同一数据源

### 缓存策略
- 现有的数据库缓存机制保持不变
- 历史数据优先查库，避免重复 API 调用

---

## 10. 后续优化建议

### 短期优化
- [ ] 添加 AkShare 财务指标接口（补充 PE/PB/市值等）
- [ ] 优化期货主力合约查询逻辑
- [ ] 添加更详细的性能监控日志

### 长期优化
- [ ] 考虑引入 Redis 缓存热点数据
- [ ] 实现数据源健康检查和自动切换
- [ ] 支持更多期货品种和国际市场

---

## 文件修改清单

- ✅ `backend/requirements.txt` - 添加 akshare 依赖
- ✅ `backend/services/market_data.py` - 主要重构文件
  - 新增日期格式化函数
  - 新增 AkShare 数据获取函数
  - 重构 `fetch_stock_data()` 实现混合路由
  - 增强错误处理和日志记录

---

## 总结

本次重构成功实现了以下目标：

1. ✅ **修复日期格式 Bug** - 统一使用 YYYY-MM-DD 格式
2. ✅ **引入 AkShare** - 规避 yfinance 频率限制
3. ✅ **实现混合路由** - 智能选择最优数据源
4. ✅ **异常降级策略** - 自动处理 RateLimitError
5. ✅ **数据格式对齐** - 保证前端兼容性

系统现在具有更强的稳定性和容错能力，能够应对不同数据源的限制和故障，为用户提供更可靠的数据服务。
