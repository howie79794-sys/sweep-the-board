"""
Hugging Face Spaces入口文件
由于Hugging Face Spaces对Node.js支持有限，这里提供FastAPI后端服务
前端需要静态导出或使用其他方案
"""
import os
import sys
from pathlib import Path

# 添加backend目录到路径
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from api.main import app

# Hugging Face Spaces会自动识别app对象
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
