"""
Hugging Face Spaces入口文件
由于使用 Docker 部署，直接使用 start.sh 启动脚本
此文件保留作为备用入口
"""
import subprocess
import sys
import os

# 切换到项目根目录
os.chdir('/app')

# 执行启动脚本
if __name__ == "__main__":
    subprocess.run(['/app/start.sh'])
