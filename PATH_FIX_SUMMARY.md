# 路径切换逻辑修复总结

## 问题描述

本地启动时报错：
```
FileNotFoundError: [Errno 2] No such file or directory: '/app'
```

**原因**：代码中硬编码了 `/app` 路径，仅适用于 Docker 容器环境，在本地开发环境中会失败。

## 修复内容

### 1. ✅ 修复 `app.py`

**位置**：项目根目录

**变更前**：
```python
# 切换到项目根目录
os.chdir('/app')

# 执行启动脚本
if __name__ == "__main__":
    subprocess.run(['/app/start.sh'])
```

**变更后**：
```python
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
```

**改进点**：
- ✅ 环境自动检测：云端使用 `/app`，本地使用脚本所在目录
- ✅ 友好的错误提示：脚本不存在时给出详细信息
- ✅ 使用 `Path` 对象处理路径，更加健壮

### 2. ✅ 修复 `start.sh`

**位置**：项目根目录

**变更前**：
```bash
# 创建数据目录（用于头像文件存储）
mkdir -p /app/data/avatars

# 初始化数据库表结构
cd /app/backend
PYTHONPATH=/app/backend python3 -m database.init_db

# 启动后端 FastAPI
cd /app/backend
PYTHONPATH=/app/backend uvicorn main:app --host 0.0.0.0 --port 8000 &

# 启动前端 Next.js
cd /app/frontend
PORT=7860 HOSTNAME=0.0.0.0 npm run start &
```

**变更后**：
```bash
# 检测项目根目录（适配本地和云端）
if [ -d "/app" ] && [ -d "/app/backend" ]; then
    # 云端环境（Docker）
    APP_ROOT="/app"
    echo "📍 运行环境: 云端 (Docker)"
else
    # 本地环境
    APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    echo "📍 运行环境: 本地开发"
fi

echo "📂 项目根目录: $APP_ROOT"

# 创建数据目录
mkdir -p "$APP_ROOT/data/avatars"

# 初始化数据库表结构
cd "$APP_ROOT/backend"
PYTHONPATH="$APP_ROOT/backend" python3 -m database.init_db

# 启动后端 FastAPI
cd "$APP_ROOT/backend"
PYTHONPATH="$APP_ROOT/backend" uvicorn main:app --host 0.0.0.0 --port 8000 &

# 启动前端 Next.js
cd "$APP_ROOT/frontend"
PORT=7860 HOSTNAME=0.0.0.0 npm run start &
```

**改进点**：
- ✅ 环境自动检测：根据目录是否存在判断运行环境
- ✅ 显示运行环境：清晰标识当前是云端还是本地
- ✅ 统一使用 `$APP_ROOT` 变量，所有路径一处修改

### 3. ✅ 验证其他脚本

已检查以下脚本，**无需修改**（它们已使用相对路径）：

- ✅ `start_backend.sh` - 使用 `cd "$(dirname "$0")/backend"`
- ✅ `START_SERVERS.sh` - 使用 `SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"`
- ✅ `START_FRONTEND.sh` - 使用 `cd "$(dirname "$0")/frontend"`
- ✅ `backend/config.py` - 使用 `Path(__file__).parent.parent`
- ✅ `backend/run.py` - 使用配置文件中的变量

## 使用方法

### 本地开发环境

```bash
# 方法 1: 直接运行 Python 脚本
python3 app.py

# 方法 2: 运行启动脚本
./start.sh

# 方法 3: 分别启动前后端
./start_backend.sh
./START_FRONTEND.sh
```

### 云端环境（Docker/Hugging Face）

```bash
# Docker 容器中会自动使用 /app 路径
python3 app.py
```

## 测试清单

- [x] 本地运行 `python3 app.py` 不报路径错误
- [x] 本地运行 `./start.sh` 正常启动
- [x] 云端 Docker 环境正常启动
- [x] 所有路径都使用相对路径或环境检测

## 技术要点

### Python 路径处理最佳实践

```python
from pathlib import Path

# ✅ 推荐：使用 Path 对象
script_dir = Path(__file__).parent.absolute()

# ❌ 不推荐：硬编码绝对路径
script_dir = "/app"
```

### Bash 路径处理最佳实践

```bash
# ✅ 推荐：自动检测脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ❌ 不推荐：硬编码绝对路径
SCRIPT_DIR="/app"
```

## 相关文件

- `app.py` - Hugging Face Spaces 入口文件
- `start.sh` - 主启动脚本
- `backend/config.py` - 后端配置文件
- `start_backend.sh` - 后端启动脚本
- `START_SERVERS.sh` - 前后端联合启动脚本
- `START_FRONTEND.sh` - 前端启动脚本

## 注意事项

1. **环境变量**：确保 `DATABASE_URL` 已设置
2. **依赖安装**：确保已安装 Python 和 Node.js 依赖
3. **权限问题**：启动脚本需要执行权限（`chmod +x *.sh`）
4. **端口占用**：确保 8000 和 7860 端口未被占用

## 兼容性

- ✅ 本地开发环境（macOS, Linux, Windows WSL）
- ✅ Docker 容器环境
- ✅ Hugging Face Spaces
- ✅ 其他云端部署平台

## 回滚

如果修复后出现问题，可以回滚到之前的版本：

```bash
git checkout HEAD~1 app.py start.sh
```

## 总结

本次修复确保了项目可以在本地和云端环境中无缝运行，不再依赖硬编码的 `/app` 路径。所有路径处理都遵循最佳实践，使用相对路径和环境检测。
