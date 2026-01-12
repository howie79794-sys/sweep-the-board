#!/usr/bin/env python3
"""
测试数据获取服务
用于验证 yfinance 和 baostock 的集成
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from services.data_fetcher import (
    normalize_stock_code,
    convert_to_yfinance_symbol,
    fetch_stock_data,
    fetch_asset_data,
    YFINANCE_AVAILABLE,
    BAOSTOCK_AVAILABLE
)

def test_code_conversion():
    """测试代码转换功能"""
    print("=" * 60)
    print("测试代码转换功能")
    print("=" * 60)
    
    test_cases = [
        ("SH601727", "601727.SS"),
        ("SZ300857", "300857.SZ"),
        ("601727", "601727.SS"),
        ("300857", "300857.SZ"),
        ("000001", "000001.SZ"),
    ]
    
    for input_code, expected_suffix in test_cases:
        normalized = normalize_stock_code(input_code)
        yf_symbol = convert_to_yfinance_symbol(input_code)
        print(f"输入: {input_code:10} -> 标准化: {normalized:10} -> yfinance: {yf_symbol:15}")
        assert yf_symbol.endswith(expected_suffix), f"期望以 {expected_suffix} 结尾，但得到 {yf_symbol}"
    
    print("✓ 代码转换测试通过\n")


def test_data_fetch():
    """测试数据获取功能"""
    print("=" * 60)
    print("测试数据获取功能")
    print("=" * 60)
    
    print(f"yfinance 可用: {YFINANCE_AVAILABLE}")
    print(f"baostock 可用: {BAOSTOCK_AVAILABLE}\n")
    
    # 测试代码
    test_code = "601727"  # 上海电气
    start_date = "2026-01-05"
    end_date = "2026-01-10"
    
    print(f"测试获取股票数据:")
    print(f"  代码: {test_code}")
    print(f"  日期范围: {start_date} 至 {end_date}\n")
    
    try:
        df = fetch_stock_data(test_code, start_date, end_date)
        if df is not None and not df.empty:
            print(f"✓ 成功获取数据: {len(df)} 条记录")
            print(f"  列名: {list(df.columns)}")
            print(f"  前5行数据:")
            print(df.head().to_string())
        else:
            print("⚠ 未获取到数据（可能是网络问题或日期范围内无数据）")
    except Exception as e:
        print(f"✗ 获取数据时出错: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()


def test_fetch_asset_data():
    """测试统一的资产数据获取接口"""
    print("=" * 60)
    print("测试统一的资产数据获取接口")
    print("=" * 60)
    
    test_code = "601727"
    start_date = "2026-01-05"
    end_date = "2026-01-10"
    
    print(f"测试获取资产数据:")
    print(f"  代码: {test_code}")
    print(f"  类型: stock")
    print(f"  日期范围: {start_date} 至 {end_date}\n")
    
    try:
        result = fetch_asset_data(test_code, "stock", start_date, end_date)
        if result:
            print(f"✓ 成功获取数据: {len(result)} 条记录")
            print(f"  第一条数据示例:")
            if result:
                first = result[0]
                print(f"    日期: {first.get('date')}")
                print(f"    收盘价: {first.get('close_price')}")
                print(f"    成交量: {first.get('volume')}")
        else:
            print("⚠ 未获取到数据（可能是网络问题或日期范围内无数据）")
    except Exception as e:
        print(f"✗ 获取数据时出错: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()


def test_error_handling():
    """测试错误处理（确保不会抛出异常）"""
    print("=" * 60)
    print("测试错误处理")
    print("=" * 60)
    
    # 测试无效代码
    invalid_codes = ["999999", "INVALID"]
    
    for code in invalid_codes:
        print(f"测试无效代码: {code}")
        try:
            result = fetch_stock_data(code, "2026-01-05", "2026-01-10")
            if result is None:
                print(f"  ✓ 正确处理：返回 None（没有抛出异常）")
            else:
                print(f"  ⚠ 返回了数据（可能代码有效）")
        except Exception as e:
            print(f"  ✗ 抛出了异常: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("数据获取服务测试")
    print("=" * 60 + "\n")
    
    try:
        # 测试代码转换
        test_code_conversion()
        
        # 测试数据获取（需要网络连接）
        print("注意: 以下测试需要网络连接")
        print("如果没有网络，测试可能会失败，但不会导致服务崩溃\n")
        
        test_data_fetch()
        test_fetch_asset_data()
        test_error_handling()
        
        print("=" * 60)
        print("测试完成")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n测试过程中发生未预期的错误: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
