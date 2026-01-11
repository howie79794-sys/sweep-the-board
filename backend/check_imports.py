"""检查导入问题"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

try:
    print("1. 测试config导入...")
    from config import UPLOAD_DIR, MAX_UPLOAD_SIZE, ALLOWED_EXTENSIONS
    print(f"   UPLOAD_DIR: {UPLOAD_DIR}")
    print(f"   MAX_UPLOAD_SIZE: {MAX_UPLOAD_SIZE}")
    print("   OK")
except Exception as e:
    print(f"   错误: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n2. 测试database导入...")
    from database.base import get_db, SessionLocal
    print("   OK")
except Exception as e:
    print(f"   错误: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n3. 测试models导入...")
    from models.user import User
    print("   OK")
except Exception as e:
    print(f"   错误: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n4. 测试路由导入...")
    from api.routes.users import router
    print("   OK")
except Exception as e:
    print(f"   错误: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n5. 测试API主应用导入...")
    from api.main import app
    print("   OK")
except Exception as e:
    print(f"   错误: {e}")
    import traceback
    traceback.print_exc()
