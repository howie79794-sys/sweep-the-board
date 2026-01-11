---
title: CoolDown龙虎榜
emoji: 🏆
colorFrom: yellow
colorTo: orange
sdk: docker
sdk_version: 4.4.1
app_file: app.py
pinned: false
license: mit
---

# CoolDown龙虎榜

金融资产排行榜网站

## 部署说明

由于Hugging Face Spaces对Node.js支持有限，当前部署方案：

1. **后端API**: 使用FastAPI（通过app.py）
2. **前端**: 需要静态导出或使用替代方案

### 方案A：静态导出前端

```bash
cd frontend
npm run build
npm run export  # 如果配置了静态导出
```

然后将静态文件复制到Spaces的public目录。

### 方案B：使用Gradio/Streamlit

如果静态导出不可行，可以考虑使用Gradio或Streamlit重建前端界面。

## 环境变量

- `DATABASE_URL`: 数据库URL（默认使用SQLite）
- `API_HOST`: API主机（默认0.0.0.0）
- `API_PORT`: API端口（默认7860，Spaces使用此端口）
