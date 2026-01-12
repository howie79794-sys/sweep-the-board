#!/usr/bin/env python3
"""
检查后端服务状态和数据库状态
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database.base import SessionLocal
from models.user import User
from models.asset import Asset

print("=" * 60)
print("后端服务和数据库状态检查")
print("=" * 60)

# 检查数据库连接
try:
    db = SessionLocal()
    print("\n✓ 数据库连接成功")
    
    # 检查用户数据
    users = db.query(User).all()
    print(f"\n用户数据: {len(users)} 个用户")
    for user in users[:5]:
        print(f"  - ID: {user.id}, 名称: {user.name}, 活跃: {user.is_active}")
    
    # 检查资产数据
    assets = db.query(Asset).all()
    print(f"\n资产数据: {len(assets)} 个资产")
    for asset in assets[:5]:
        print(f"  - ID: {asset.id}, 名称: {asset.name}, 代码: {asset.code}, 用户ID: {asset.user_id}")
    
    db.close()
    print("\n✓ 数据库查询成功")
    
except Exception as e:
    print(f"\n✗ 数据库错误: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("检查完成")
print("=" * 60)
