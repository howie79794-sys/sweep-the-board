"""测试API端点"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database.base import SessionLocal
from models.user import User

try:
    db = SessionLocal()
    users = db.query(User).all()
    print(f"成功查询到 {len(users)} 个用户")
    for user in users:
        print(f"  - {user.id}: {user.name}")
    db.close()
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
