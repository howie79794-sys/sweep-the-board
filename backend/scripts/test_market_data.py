#!/usr/bin/env python3
"""
市场数据服务测试脚本
用于验证 yfinance + AkShare 混合路由是否正常工作
"""
import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.market_data import (
    fetch_stock_data,
    normalize_date_format,
    AKSHARE_AVAILABLE,
    YFINANCE_AVAILABLE,
    BAOSTOCK_AVAILABLE
)

def test_date_format():
    """测试日期格式标准化"""
    print("\n" + "="*60)
    print("测试 1: 日期格式标准化")
    print("="*60)
    
    test_cases = [
        "2026-01-19",
        "2026/01/19",
        "20260119"
    ]
    
    for date_str in test_cases:
        try:
            result = normalize_date_format(date_str)
            print(f"✓ {date_str:15} → {result}")
        except Exception as e:
            print(f"✗ {date_str:15} → 错误: {str(e)}")

def test_a_stock():
    """测试A股数据获取"""
    print("\n" + "="*60)
    print("测试 2: A股数据获取（混合路由）")
    print("="*60)
    
    test_codes = [
        ("SH.600519", "贵州茅台（上海）"),
        ("601727", "上海电气（格式兼容）"),
        ("SZ.000001", "平安银行（深圳）"),
        ("300857", "协创数据（格式兼容）"),
    ]
    
    for code, name in test_codes:
        print(f"\n测试 {name}: {code}")
        try:
            df = fetch_stock_data(code, "2026-01-15", "2026-01-19")
            if df is not None and not df.empty:
                print(f"  ✓ 成功获取 {len(df)} 条数据")
                print(f"  - 日期范围: {df['date'].min()} 至 {df['date'].max()}")
                print(f"  - 列: {', '.join(df.columns.tolist()[:5])}...")
            else:
                print(f"  ✗ 未获取到数据")
        except Exception as e:
            print(f"  ✗ 错误: {type(e).__name__}: {str(e)}")

def test_futures():
    """测试股指期货数据获取"""
    print("\n" + "="*60)
    print("测试 3: 股指期货数据获取（AkShare）")
    print("="*60)
    
    if not AKSHARE_AVAILABLE:
        print("⚠️  AkShare 未安装，跳过期货测试")
        return
    
    test_codes = [
        ("CF.IF0", "沪深300股指期货"),
        ("CF.IC0", "中证500股指期货"),
        ("CF.IH0", "上证50股指期货"),
    ]
    
    for code, name in test_codes:
        print(f"\n测试 {name}: {code}")
        try:
            df = fetch_stock_data(code, "2026-01-15", "2026-01-19")
            if df is not None and not df.empty:
                print(f"  ✓ 成功获取 {len(df)} 条数据")
                print(f"  - 日期范围: {df['date'].min()} 至 {df['date'].max()}")
            else:
                print(f"  ✗ 未获取到数据")
        except Exception as e:
            print(f"  ✗ 错误: {type(e).__name__}: {str(e)}")

def test_us_stock():
    """测试美股数据获取"""
    print("\n" + "="*60)
    print("测试 4: 美股数据获取（yfinance）")
    print("="*60)
    
    if not YFINANCE_AVAILABLE:
        print("⚠️  yfinance 未安装，跳过美股测试")
        return
    
    test_codes = [
        ("AAPL", "苹果"),
        ("US.MSFT", "微软（带前缀）"),
    ]
    
    for code, name in test_codes:
        print(f"\n测试 {name}: {code}")
        try:
            df = fetch_stock_data(code, "2026-01-15", "2026-01-19")
            if df is not None and not df.empty:
                print(f"  ✓ 成功获取 {len(df)} 条数据")
                print(f"  - 日期范围: {df['date'].min()} 至 {df['date'].max()}")
            else:
                print(f"  ✗ 未获取到数据")
        except Exception as e:
            print(f"  ✗ 错误: {type(e).__name__}: {str(e)}")

def print_summary():
    """打印数据源可用性总结"""
    print("\n" + "="*60)
    print("数据源可用性检查")
    print("="*60)
    
    sources = [
        ("yfinance", YFINANCE_AVAILABLE),
        ("baostock", BAOSTOCK_AVAILABLE),
        ("akshare", AKSHARE_AVAILABLE)
    ]
    
    for name, available in sources:
        status = "✓ 可用" if available else "✗ 不可用"
        print(f"  {name:12} {status}")

if __name__ == "__main__":
    print("\n" + "#"*60)
    print("# 市场数据服务测试")
    print("#"*60)
    
    # 打印数据源可用性
    print_summary()
    
    # 运行测试
    test_date_format()
    test_a_stock()
    test_futures()
    test_us_stock()
    
    print("\n" + "#"*60)
    print("# 测试完成")
    print("#"*60)
    print("\n提示：如果看到 '✓ 成功获取' 说明该数据源工作正常")
    print("      如果看到 '✗ 未获取到数据' 可能是网络问题或API限制")
    print()
