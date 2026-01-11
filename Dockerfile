FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制后端代码
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# 复制所有代码
COPY . /app/

# 设置Python路径
ENV PYTHONPATH=/app/backend

# 初始化数据库
RUN python3 -m backend.database.init_db || true

# 暴露端口
EXPOSE 7860

# 启动应用
CMD ["python3", "app.py"]
