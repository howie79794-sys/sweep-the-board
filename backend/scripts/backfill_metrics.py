#!/usr/bin/env python3
"""
历史财务数据补录脚本
用于填充 2026-01-05 至 2026-01-12 之间缺失的财务指标数据
"""
import sys
import os
from datetime import date
from pathlib import Path

# 添加 backend 目录到 Python 路径
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from sqlalchemy.orm import Session
from database.config import SessionLocal
from database.models import Asset, MarketData


def backfill_historical_metrics():
    """
    补录历史财务指标数据
    
    逻辑：
    1. 遍历所有资产
    2. 获取每个资产 1月13日 的最新财务指标（作为基准）
    3. 查找该资产在 2026-01-05 至 2026-01-12 之间所有 pe_ratio 为空的记录
    4. 根据股价波动比例反推历史指标
    5. 批量更新数据库
    """
    db: Session = SessionLocal()
    
    try:
        # 定义日期范围
        start_date = date(2026, 1, 5)
        end_date = date(2026, 1, 12)
        reference_date = date(2026, 1, 13)  # 基准日期
        
        print(f"[补录脚本] ========== 开始历史财务数据补录 ==========")
        print(f"[补录脚本] 补录日期范围: {start_date} 至 {end_date}")
        print(f"[补录脚本] 基准日期: {reference_date}")
        
        # 获取所有资产
        assets = db.query(Asset).all()
        print(f"[补录脚本] 找到 {len(assets)} 个资产需要处理")
        
        total_updated = 0
        
        for asset in assets:
            print(f"\n[补录脚本] -------- 处理资产: {asset.name} (ID: {asset.id}, 代码: {asset.code}) --------")
            
            # 获取基准日期的财务指标（1月13日）
            reference_data = db.query(MarketData).filter(
                MarketData.asset_id == asset.id,
                MarketData.date == reference_date
            ).first()
            
            if not reference_data:
                print(f"[补录脚本] 警告: 资产 {asset.name} 在基准日期 {reference_date} 没有数据，跳过")
                continue
            
            # 检查基准数据是否有财务指标
            if reference_data.pe_ratio is None or reference_data.pe_ratio == 0:
                print(f"[补录脚本] 警告: 资产 {asset.name} 在基准日期没有有效的财务指标，跳过")
                continue
            
            # 获取基准值
            ref_pe = reference_data.pe_ratio
            ref_pb = reference_data.pb_ratio if reference_data.pb_ratio else None
            ref_market_cap = reference_data.market_cap if reference_data.market_cap and reference_data.market_cap > 0 else None
            ref_eps = reference_data.eps_forecast if reference_data.eps_forecast else None
            ref_price = reference_data.close_price
            
            print(f"[补录脚本] 基准数据 (日期: {reference_date}):")
            print(f"[补录脚本]   价格: {ref_price}")
            print(f"[补录脚本]   PE: {ref_pe}")
            print(f"[补录脚本]   PB: {ref_pb}")
            print(f"[补录脚本]   市值: {ref_market_cap}")
            print(f"[补录脚本]   EPS: {ref_eps}")
            
            # 查找需要补录的历史记录（pe_ratio 为空的记录）
            historical_records = db.query(MarketData).filter(
                MarketData.asset_id == asset.id,
                MarketData.date >= start_date,
                MarketData.date <= end_date,
                (MarketData.pe_ratio.is_(None) | (MarketData.pe_ratio == 0))
            ).order_by(MarketData.date.asc()).all()
            
            if not historical_records:
                print(f"[补录脚本] 资产 {asset.name} 在日期范围内没有需要补录的记录")
                continue
            
            print(f"[补录脚本] 找到 {len(historical_records)} 条需要补录的记录")
            
            # 计算并更新每条记录
            updated_count = 0
            for hist_record in historical_records:
                hist_price = hist_record.close_price
                
                if hist_price is None or hist_price == 0:
                    print(f"[补录脚本] 警告: 记录日期 {hist_record.date} 的价格为空或0，跳过")
                    continue
                
                if ref_price is None or ref_price == 0:
                    print(f"[补录脚本] 警告: 基准价格为空或0，跳过")
                    continue
                
                # 计算价格比例
                price_ratio = hist_price / ref_price
                
                # 根据股价波动比例反推历史指标
                # hist_pe = today_pe * (hist_price / today_price)
                hist_pe = ref_pe * price_ratio
                
                # hist_pb = today_pb * (hist_price / today_price)
                hist_pb = ref_pb * price_ratio if ref_pb else None
                
                # hist_market_cap = today_market_cap * (hist_price / today_price)
                hist_market_cap = ref_market_cap * price_ratio if ref_market_cap else None
                
                # hist_eps = today_eps（假设 EPS 短期不变）
                hist_eps = ref_eps
                
                # 更新记录
                hist_record.pe_ratio = hist_pe
                if hist_pb is not None:
                    hist_record.pb_ratio = hist_pb
                if hist_market_cap is not None:
                    hist_record.market_cap = hist_market_cap
                if hist_eps is not None:
                    hist_record.eps_forecast = hist_eps
                
                updated_count += 1
                
                print(f"[补录脚本]   更新记录 (日期: {hist_record.date}): PE={hist_pe:.2f}, PB={hist_pb:.2f if hist_pb else 'N/A'}, 市值={hist_market_cap:.2f if hist_market_cap else 'N/A'}, EPS={hist_eps if hist_eps else 'N/A'}")
            
            # 提交当前资产的更新
            if updated_count > 0:
                db.commit()
                print(f"[补录脚本] ✓ 资产 {asset.name} 成功补录 {updated_count} 条记录")
                total_updated += updated_count
            else:
                print(f"[补录脚本] 资产 {asset.name} 没有需要更新的记录")
        
        print(f"\n[补录脚本] ========== 历史数据补录完成 ==========")
        print(f"[补录脚本] 总计更新: {total_updated} 条记录")
        
        return total_updated
        
    except Exception as e:
        print(f"[补录脚本] 错误: 补录过程中发生异常: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("[补录脚本] 启动历史财务数据补录脚本...")
    
    # 检查环境变量
    if not os.getenv("DATABASE_URL"):
        print("[补录脚本] 错误: DATABASE_URL 环境变量未设置")
        print("[补录脚本] 请设置环境变量，例如:")
        print("[补录脚本]   export DATABASE_URL='your_database_url'")
        print("[补录脚本]   或")
        print("[补录脚本]   DATABASE_URL='your_database_url' python3 scripts/backfill_metrics.py")
        sys.exit(1)
    
    try:
        updated_count = backfill_historical_metrics()
        print(f"[补录脚本] 脚本执行完成，共更新 {updated_count} 条记录")
        sys.exit(0)
    except Exception as e:
        print(f"[补录脚本] 脚本执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
