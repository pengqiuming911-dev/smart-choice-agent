"""
测试飞书推送
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv("../.env")

from src.config import settings
from src.sender import get_sender
from src.market_data import get_indices_batch
from src.feishu_bitable import query_product_table
from src.jobs.report_builder import parse_product_record, build_index_section, build_product_section

print(f"Target open_id: {settings.scheduler_target_open_id}")
print(f"Feishu app_id: {settings.feishu_app_id}")
print()

# 测试1：发送纯文本报告
print("=" * 60)
print("1. 发送纯文本报告测试")
print("=" * 60)

indices = get_indices_batch(settings.indices_list)
print(f"获取到 {len(indices)} 个指数")

raw_products = query_product_table()
products = [p for p in (parse_product_record(r) for r in raw_products) if p]
print(f"获取到 {len(products)} 个产品")

# 构建纯文本报告
index_text = build_index_section(indices) if indices else "暂无指数数据"
product_text = build_product_section(products[:5])  # 只取前5个

from datetime import datetime
date_str = datetime.now().strftime("%Y年%m月%d日")
report = f"📊 【收盘简报】{date_str}\n\n{index_text}\n\n{product_text}\n\n---\n⚠️ 本报告仅供参考，不构成投资建议。"

print(f"\n报告长度: {len(report)} 字符")
print(f"\n报告预览（前500字）:\n{report[:500]}...")

# 发送到飞书
sender = get_sender()
print(f"\n正在发送到飞书 {settings.scheduler_target_open_id}...")
success = sender.send_message(settings.scheduler_target_open_id, report)
print(f"发送结果: {'✅ 成功' if success else '❌ 失败'}")
