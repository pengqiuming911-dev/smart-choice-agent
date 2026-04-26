"""
Local data verification script (no Feishu push required)
Test AKShare index data + Feishu Bitable product data
"""
import sys
import os
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv("../.env")

from src.config import settings
from src.market_data import get_indices_batch
from src.feishu_bitable import query_product_table, get_field_names
from src.jobs.report_builder import parse_product_record, build_index_section, build_product_section


def test_akshare():
    print("=" * 60)
    print("1. AKShare 指数行情测试")
    print("=" * 60)

    indices = get_indices_batch(settings.indices_list)

    if not indices:
        print("❌ 未获取到任何指数数据")
    else:
        print(f"✅ 成功获取 {len(indices)} 个指数数据：")
        for idx in indices:
            sign = "+" if idx["change"] >= 0 else ""
            print(
                f"  {idx['name']}: {idx['current']:.2f} "
                f"{sign}{idx['change']:.2f} ({sign}{idx['change_pct']:.2f}%)"
            )

    print()
    return indices


def test_bitable_fields():
    print("=" * 60)
    print("2. 飞书 Bitable 字段名测试")
    print("=" * 60)

    field_names = get_field_names()

    if not field_names:
        print("❌ 未获取到字段名列表")
    else:
        print(f"✅ 成功获取 {len(field_names)} 个字段：")
        for name in field_names:
            print(f"  - {name}")

    print()
    return field_names


def test_bitable_products():
    print("=" * 60)
    print("3. 飞书 Bitable 产品数据测试")
    print("=" * 60)

    raw_products = query_product_table()

    if not raw_products:
        print("❌ 未获取到任何产品数据")
        return []

    print(f"✅ 成功获取 {len(raw_products)} 条产品记录")

    # 解析每条记录
    products = []
    for i, raw in enumerate(raw_products):
        parsed = parse_product_record(raw)
        if parsed:
            products.append(parsed)
            print(f"\n  【产品 {i+1}】")
            print(f"  航班编号: {parsed['flight_no']}")
            print(f"  代码: {parsed['code']}")
            print(f"  结构类型: {parsed['structure_type']}")
            print(f"  入场价: {parsed['entry_display']}")
            print(f"  敲出: {parsed['knock_out_pct_display']}")
            print(f"  首敲点位: {parsed['first_knock_out_display']}")
            print(f"  锁定期: {parsed['lock_period']}月")
            print(f"  期限: {parsed['term']}月")
            print(f"  降落伞: {parsed['parachute_display']}")
            print(f"  月票息: {parsed['monthly_coupon_display']}")
            print(f"  第一段票息: {parsed['tier1_coupon_display']}")
            print(f"  保证金比例: {parsed['margin_display']}")
            print(f"  客户数: {parsed['customer_count']}")

            # 显示敲出点位序列（前3个）
            if parsed["ko_series"]:
                print(f"  敲出点位序列:")
                for ko in parsed["ko_series"][:3]:
                    print(f"    第{ko['month']}月: {ko['knock_out_price']/10000:.2f}万")
        else:
            print(f"\n  【产品 {i+1}】解析失败: {raw.get('航班编号', raw.get('产品名称', '???'))}")

    print()
    return products


def test_report_text(indices, products):
    print("=" * 60)
    print("4. 生成的文本报告预览")
    print("=" * 60)

    index_text = build_index_section(indices)
    product_text = build_product_section(products)

    print(index_text)
    print()
    print(product_text)
    print()
    print("⚠️ 风险提示已附加（报告中会自动添加）")


def main():
    print("\n" + "=" * 60)
    print("scheduler_service 本地数据验证")
    print("=" * 60)
    print()

    # 1. AKShare 测试
    indices = test_akshare()

    # 2. Bitable 字段名测试
    field_names = test_bitable_fields()

    # 3. Bitable 产品数据测试
    products = test_bitable_products()

    # 4. 生成文本报告
    if indices or products:
        test_report_text(indices, products)

    print("=" * 60)
    print("验证完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
