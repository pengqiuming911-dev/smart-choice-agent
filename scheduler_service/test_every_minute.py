"""
每分钟发送测试 - 用于验证飞书推送
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import time
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, ".")
load_dotenv("../.env")

from src.config import settings
from src.sender import get_sender
from src.market_data import get_indices_batch
from src.feishu_bitable import query_product_table
from src.jobs.report_builder import parse_product_record, build_index_section, build_product_section

print(f"每分钟发送测试开始...")
print(f"推送目标: {settings.scheduler_target_open_id}")
print(f"按 Ctrl+C 停止")
print()

def build_report():
    indices = get_indices_batch(settings.indices_list)
    raw_products = query_product_table()
    products = [p for p in (parse_product_record(r) for r in raw_products) if p]

    index_text = build_index_section(indices) if indices else "暂无指数数据"
    product_text = build_product_section(products[:3])  # 只取前3个

    now = datetime.now()
    date_str = now.strftime("%Y年%m月%d日 %H:%M:%S")
    report = (
        f"🕐 【每分钟测试】{date_str}\n"
        f"(AKShare 代理问题，指数数据暂缺)\n\n"
        f"{index_text}\n\n{product_text}\n\n"
        f"---\n⚠️ 本报告仅供参考，不构成投资建议。"
    )
    return report

sender = get_sender()
count = 0

while True:
    count += 1
    now = datetime.now()
    print(f"[{now.strftime('%H:%M:%S')}] 第 {count} 次发送...")

    report = build_report()
    success = sender.send_message(settings.scheduler_target_open_id, report)

    if success:
        print(f"  ✅ 成功")
    else:
        print(f"  ❌ 失败")

    time.sleep(60)  # 等待60秒
