FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# 复制后端代码和依赖
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r backend/requirements.txt && \
    pip install --upgrade akshare

# 复制所有代码
COPY . /app/

# 安装前端依赖
RUN cd frontend && npm install

# 构建前端（不使用standalone模式，以支持rewrites）
RUN cd frontend && npm run build

# 设置Python路径
ENV PYTHONPATH=/app/backend

# 复制启动脚本并设置权限
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# 暴露端口（Hugging Face 使用 7860）
EXPOSE 7860

# 使用启动脚本
CMD ["/app/start.sh"]
