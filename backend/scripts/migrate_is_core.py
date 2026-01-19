#!/usr/bin/env python3
"""
资产分级数据迁移脚本
用于迁移现有资产数据，设置 is_core 字段
实现"一用户一心"原则：每个用户只能有一个核心资产
"""
import sys
import os
from pathlib import Path

# 添加 backend 目录到 Python 路径
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from sqlalchemy.orm import Session
from sqlalchemy import func
from database.config import SessionLocal
from database.models import Asset


def migrate_is_core():
    """
    迁移 is_core 字段
    
    逻辑：
    1. 获取所有资产
    2. 按 user_id 分组
    3. 对于每个用户：
       - 如果只有一个资产，设置 is_core=True
       - 如果有多个资产，只将 id 最小（最早创建）的设置为 is_core=True，其余为 False
    """
    db: Session = SessionLocal()
    
    try:
        print(f"[迁移脚本] ========== 开始 is_core 字段数据迁移 ==========")
        
        # 获取所有资产
        assets = db.query(Asset).order_by(Asset.user_id, Asset.id).all()
        print(f"[迁移脚本] 找到 {len(assets)} 个资产需要处理")
        
        if not assets:
            print(f"[迁移脚本] 没有资产需要迁移")
            return 0
        
        # 按 user_id 分组
        user_assets = {}
        for asset in assets:
            if asset.user_id not in user_assets:
                user_assets[asset.user_id] = []
            user_assets[asset.user_id].append(asset)
        
        print(f"[迁移脚本] 发现 {len(user_assets)} 个用户拥有资产")
        
        total_updated = 0
        core_count = 0
        
        # 处理每个用户的资产
        for user_id, user_asset_list in user_assets.items():
            print(f"\n[迁移脚本] -------- 处理用户 ID: {user_id} (拥有 {len(user_asset_list)} 个资产) --------")
            
            # 按 id 排序（确保 id 最小的排在前面）
            user_asset_list.sort(key=lambda a: a.id)
            
            for idx, asset in enumerate(user_asset_list):
                if idx == 0:
                    # 第一个资产（id 最小）设置为核心资产
                    asset.is_core = True
                    core_count += 1
                    print(f"[迁移脚本]   ✓ 资产 {asset.name} (ID: {asset.id}, 代码: {asset.code}) -> is_core=True (核心资产)")
                else:
                    # 其他资产设置为非核心资产
                    asset.is_core = False
                    print(f"[迁移脚本]   - 资产 {asset.name} (ID: {asset.id}, 代码: {asset.code}) -> is_core=False")
                
                total_updated += 1
        
        # 提交所有更新
        db.commit()
        
        print(f"\n[迁移脚本] ========== 数据迁移完成 ==========")
        print(f"[迁移脚本] 总计更新: {total_updated} 个资产")
        print(f"[迁移脚本] 核心资产数量: {core_count}")
        print(f"[迁移脚本] 非核心资产数量: {total_updated - core_count}")
        
        # 验证结果
        print(f"\n[迁移脚本] ========== 验证迁移结果 ==========")
        for user_id in user_assets.keys():
            core_assets = db.query(Asset).filter(
                Asset.user_id == user_id,
                Asset.is_core == True
            ).all()
            
            if len(core_assets) != 1:
                print(f"[迁移脚本] ⚠️ 警告: 用户 {user_id} 有 {len(core_assets)} 个核心资产（应该只有1个）")
            else:
                print(f"[迁移脚本] ✓ 用户 {user_id}: 1 个核心资产 (符合预期)")
        
        return total_updated
        
    except Exception as e:
        print(f"[迁移脚本] 错误: 迁移过程中发生异常: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("[迁移脚本] 启动 is_core 字段数据迁移脚本...")
    
    # 检查环境变量
    if not os.getenv("DATABASE_URL"):
        print("[迁移脚本] 错误: DATABASE_URL 环境变量未设置")
        print("[迁移脚本] 请设置环境变量，例如:")
        print("[迁移脚本]   export DATABASE_URL='your_database_url'")
        print("[迁移脚本]   或")
        print("[迁移脚本]   DATABASE_URL='your_database_url' python3 scripts/migrate_is_core.py")
        sys.exit(1)
    
    # 确认是否继续
    print("\n[迁移脚本] ⚠️  此脚本将修改数据库中的资产数据")
    print("[迁移脚本] 操作内容：")
    print("[迁移脚本]   1. 将所有现有资产标记为核心资产 (is_core=True)")
    print("[迁移脚本]   2. 如果同一用户有多个资产，仅保留 ID 最小的为核心资产")
    print("[迁移脚本]   3. 其余资产设置为非核心资产 (is_core=False)")
    
    response = input("\n[迁移脚本] 确认继续？(yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("[迁移脚本] 用户取消操作，退出脚本")
        sys.exit(0)
    
    try:
        updated_count = migrate_is_core()
        print(f"\n[迁移脚本] ✅ 脚本执行完成，共更新 {updated_count} 个资产")
        sys.exit(0)
    except Exception as e:
        print(f"\n[迁移脚本] ❌ 脚本执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
