"""
Hugging Face Spaces入口文件
由于使用 Docker 部署，直接使用 start.sh 启动脚本
此文件保留作为备用入口
支持本地和云端运行环境
"""
import subprocess
import sys
import os
from pathlib import Path

# 仅当环境下确实存在 /app 文件夹时才进行切换（适配云端）
if os.path.exists('/app'):
    os.chdir('/app')
    script_path = '/app/start.sh'
else:
    # 否则使用当前脚本所在目录（适配本地开发）
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    script_path = str(script_dir / 'start.sh')

# 执行启动脚本
if __name__ == "__main__":
    if os.path.exists(script_path):
        subprocess.run([script_path])
    else:
        print(f"错误: 启动脚本不存在: {script_path}")
        print(f"当前工作目录: {os.getcwd()}")
        print("提示: 请确保在项目根目录运行此脚本")
        sys.exit(1)
