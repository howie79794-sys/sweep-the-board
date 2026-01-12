"""数据库初始化脚本
重要：此脚本仅创建表结构，绝不会创建任何测试数据。
所有数据必须通过网页管理界面手动创建，确保生产数据永远不会被覆盖。
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from database.config import Base, init_db

if __name__ == "__main__":
    try:
        # 创建所有表（如果不存在）
        print("[数据库初始化] 正在创建表结构...")
        init_db()
        print("[数据库初始化] ✓ 表结构创建完成")
        print("[数据库初始化] 📌 注意：不会创建任何测试数据，所有数据需通过管理界面手动创建")
        
    except Exception as e:
        print(f"[数据库初始化] ❌ 创建表结构时出错: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise  # 表创建失败应该抛出异常，因为这是关键步骤
