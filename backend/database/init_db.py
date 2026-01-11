"""数据库初始化脚本"""
import os
import sys
from pathlib import Path
from datetime import date, datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy.orm import Session
from database.base import SessionLocal, engine, Base
from models.user import User
from models.asset import Asset
from config import BASELINE_DATE

# 创建表
Base.metadata.create_all(bind=engine)

def init_db():
    """初始化数据库，如果数据库已存在且有数据，则跳过初始化"""
    db: Session = SessionLocal()
    
    try:
        # 检查是否已有用户数据
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"数据库已存在 {existing_users} 个用户，跳过初始化")
            return
        
        # 创建初始用户（占位符）
        users_data = [
            {"name": f"用户{i}", "is_active": True}
            for i in range(1, 9)
        ]
        
        users = []
        for user_data in users_data:
            user = User(**user_data)
            db.add(user)
            users.append(user)
        
        db.commit()
        
        # 创建初始资产
        assets_data = [
            {"code": "300857", "name": "协创数据", "market": "深圳", "asset_type": "stock", "user_id": 1},
            {"code": "600580", "name": "卧龙电驱", "market": "上海", "asset_type": "stock", "user_id": 2},
            {"code": "601727", "name": "上海电气", "market": "上海", "asset_type": "stock", "user_id": 3},
            {"code": "601877", "name": "正泰电器", "market": "上海", "asset_type": "stock", "user_id": 4},
            {"code": "300019", "name": "硅宝科技", "market": "深圳", "asset_type": "stock", "user_id": 5},
            {"code": "002444", "name": "巨星科技", "market": "深圳", "asset_type": "stock", "user_id": 6},
            {"code": "001280", "name": "中国铀业", "market": "深圳", "asset_type": "stock", "user_id": 7},
            {"code": "513010", "name": "恒生科技ETF易方达", "market": "上海", "asset_type": "fund", "user_id": 8},
        ]
        
        baseline_date = date.fromisoformat(BASELINE_DATE) if isinstance(BASELINE_DATE, str) else BASELINE_DATE
        start_date = date(2026, 1, 6)
        end_date = date(2026, 12, 31)
        
        for asset_data in assets_data:
            # 格式化代码
            if asset_data["market"] == "深圳":
                code = f"SZ{asset_data['code']}"
            else:
                code = f"SH{asset_data['code']}"
            
            asset = Asset(
                user_id=asset_data["user_id"],
                asset_type=asset_data["asset_type"],
                market=asset_data["market"],
                code=code,
                name=asset_data["name"],
                baseline_date=baseline_date,
                start_date=start_date,
                end_date=end_date,
            )
            db.add(asset)
        
        db.commit()
        print("数据库初始化完成")
        
    except Exception as e:
        db.rollback()
        print(f"初始化数据库时出错: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
