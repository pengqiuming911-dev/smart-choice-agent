"""
Build daily market + product report for Feishu card

产品表字段（来自「产品表-同步」飞书多维表格 Bitable）:
- 航班编号 / 产品名称
- 认购日
- 结构类型
- 代码（挂钩标的，如 沪深300（000300.SH））
- 锁定期（月）
- 敲出（如 103.0 表示 103%）
- 入场价（如 159900000）
- 期限（如 24m）
- 降落伞（如 85%）
- 月票息（税费后）（如 1.80%）
- 第一段票息（税费后）（如 47.00%）
- 第二段票息（税费后）
- 第三段票息（税费后）
- 派息点位
- 保证金比例（如 20%）
- 客户数
- 每月递减（来自「每月递减参考表」spreadsheet，按航班编号查找）

每月递减参考表字段（来自飞书电子表格）:
- 航班编号
- 每月递减（如 0.5 表示 0.5%）
"""
from datetime import datetime
from typing import List, Dict, Optional
from src.market_data import get_indices_batch
from src.feishu_bitable import query_product_table, build_monthly_decrement_map
from src.config import settings

# Lazy-loaded monthly decrement map (flight_no → decrement %)
_DECREMENT_MAP: Optional[Dict[str, float]] = None


def _get_decrement_map() -> Dict[str, float]:
    """Lazy-load monthly decrement map from reference spreadsheet"""
    global _DECREMENT_MAP
    if _DECREMENT_MAP is None:
        _DECREMENT_MAP = build_monthly_decrement_map()
    return _DECREMENT_MAP


# =============================================================================
# 字段名常量（必须与飞书多维表格字段名完全一致）
# =============================================================================
F_FLIGHT_NO = "航班编号"            # 产品代码/编号
F_PRODUCT_NAME = "产品名称"          # 产品名称
F_SUBSCRIBE_DATE = "认购日"          # 认购日期
F_STRUCTURE_TYPE = "结构类型"        # 如 2段式欧式早利雪球
F_CODE = "代码"                     # 挂钩标的，如 沪深300（000300.SH）
F_LOCK_PERIOD = "锁定期（月）"       # 锁定期月数，如 30
F_KNOCK_OUT = "敲出"               # 敲出百分比，如 103.0 表示 103%
F_ENTRY_PRICE = "入场价"           # 入场价（万元）
F_KNOCK_OUT_POINT_PRE = "敲出点位"  # 预计算的敲出点位（直接从表格读取，单位万元）
F_TERM = "期限"                    # 产品期限，如 24m
F_PARACHUTE = "降落伞"             # 降落伞比例
F_MONTHLY_COUPON_AFTER_TAX = "月票息（税费后）"  # 月票息（如 1.80%）
F_TIER1_COUPON_AFTER_TAX = "第一段票息\n（税费后）"  # 第一段票息（如 47.00%）注意换行符
F_TIER2_COUPON_AFTER_TAX = "第二段票息\n（税费后）"  # 第二段
F_TIER3_COUPON_AFTER_TAX = "第三段票息\n（税费后）"  # 第三段
F_DIVIDEND_POINT = "派息点位"       # 派息点位
F_MARGIN_RATIO = "保证金比例"       # 保证金比例（如 20%）
F_CUSTOMER_COUNT = "客户\n数"         # 客户数量（注意换行符）
F_MONTHLY_DECREMENT = "每月递减"   # 每月递减比例（来自参考表格，若无则用配置）


# =============================================================================
# 敲出点位计算逻辑
# =============================================================================
def calc_knock_out_point(
    entry_price: float,
    knock_out_pct: float,
    lock_period_months: int,
) -> float:
    """
    计算第一个敲出观察日的敲出点位（入场价 × 敲出%）

    规则：
    - 首个敲出观察日 = 锁定期最后一个月
    - 敲出点位 = 入场价 × 敲出%

    Args:
        entry_price: 入场价
        knock_out_pct: 敲出百分比（如 103.0 → 1.03）
        lock_period_months: 锁定期月数

    Returns:
        第一个敲出点位
    """
    if lock_period_months <= 0 or entry_price <= 0:
        return entry_price * knock_out_pct
    return entry_price * knock_out_pct


def calc_knock_out_series(
    entry_price: float,
    knock_out_pct: float,
    lock_period_months: int,
    monthly_decrement_pct: float,
) -> List[Dict]:
    """
    计算完整敲出点位序列

    规则：
    - 第1个敲出观察日（锁定期最后一个月）：入场价 × 敲出%
    - 之后每月：入场价 × (敲出% - 每月递减% × 月份差)

    Args:
        entry_price: 入场价
        knock_out_pct: 敲出百分比（如 103.0 → 1.03）
        lock_period_months: 锁定期月数
        monthly_decrement_pct: 每月递减百分比（如 0.5 → 0.005）

    Returns:
        敲出点位列表 [{month, knock_out_price}, ...]
    """
    if lock_period_months <= 0 or entry_price <= 0:
        return []

    first_month = lock_period_months
    first_ko = entry_price * knock_out_pct

    points = [{"month": first_month, "knock_out_price": first_ko}]

    # 之后每月递减观察
    max_extra = 12  # 最多再看12个月
    for i in range(1, max_extra + 1):
        month = first_month + i
        ko = entry_price * (knock_out_pct - monthly_decrement_pct * i)
        if ko <= entry_price:  # 敲出价格不低于入场价
            break
        points.append({"month": month, "knock_out_price": ko})

    return points


# =============================================================================
# 数据解析
# =============================================================================
def to_float(val, default=0.0) -> float:
    """将各种类型转为 float"""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        s = val.strip().replace(",", "").replace("%", "").replace("％", "")
        if s in ("", "无", "None", "-", "N/A", "NA"):
            return default
        try:
            return float(s)
        except ValueError:
            return default
    return default


def to_int(val, default=0) -> int:
    """将各种类型转为 int"""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        s = val.strip().replace("m", "").replace("M", "").replace("个月", "")
        if s in ("", "无", "None", "-", "N/A", "NA"):
            return default
        try:
            return int(s)
        except ValueError:
            return default
    return default


def format_wan_yuan(amount: float) -> str:
    """将万元数值转为带单位的字符串（直接显示，不做转换）"""
    if amount >= 10000:
        return f"{amount/10000:.2f}亿"
    return f"{amount:.2f}万"


def parse_product_record(fields: Dict) -> Optional[Dict]:
    """解析一条产品记录"""
    try:
        # 产品名称（优先用航班编号，其次产品名称）
        name = fields.get(F_FLIGHT_NO) or fields.get(F_PRODUCT_NAME, "未知")
        if not name or str(name).strip() == "":
            return None

        # 数值字段
        entry_price = to_float(fields.get(F_ENTRY_PRICE, 0))          # 入场价（万元）
        knock_out_raw = to_float(fields.get(F_KNOCK_OUT, 0))          # 敲出（原始值，1.03 表示 103%）
        lock_period = to_int(fields.get(F_LOCK_PERIOD, 0))            # 锁定期月数
        term = to_int(fields.get(F_TERM, 0))                         # 期限月数
        parachute = to_float(fields.get(F_PARACHUTE, 0))              # 降落伞（如 0.85 = 85%）
        monthly_coupon = to_float(fields.get(F_MONTHLY_COUPON_AFTER_TAX, 0))
        tier1 = to_float(fields.get(F_TIER1_COUPON_AFTER_TAX, 0))
        tier2 = to_float(fields.get(F_TIER2_COUPON_AFTER_TAX, 0))
        tier3 = to_float(fields.get(F_TIER3_COUPON_AFTER_TAX, 0))
        dividend = to_float(fields.get(F_DIVIDEND_POINT, 0))         # 派息点位
        margin = to_float(fields.get(F_MARGIN_RATIO, 0))            # 保证金比例
        customer_count = to_int(fields.get(F_CUSTOMER_COUNT, 0))     # 客户数

        # 每月递减（优先级：参考表spreadsheet > Bitable字段 > 全局配置）
        flight_no_str = str(name).strip()
        decrement_map = _get_decrement_map()
        monthly_decrement = decrement_map.get(flight_no_str, None)
        if monthly_decrement is None:
            # Bitable 字段值为空/不存在时用全局配置；字段有具体值（含0）时直接用
            raw = fields.get(F_MONTHLY_DECREMENT)
            if raw is None or (isinstance(raw, str) and raw.strip() in ("", "无", "None", "-", "N/A", "NA")):
                monthly_decrement = settings.monthly_decrement
            else:
                monthly_decrement = to_float(raw)

        # 敲出点位：优先用表格预计算值（单位万元），否则自己算
        first_ko_pre = to_float(fields.get(F_KNOCK_OUT_POINT_PRE, 0))
        if first_ko_pre > 0:
            first_ko = first_ko_pre  # 直接用表格的预计算值
        else:
            # 敲出原始值 > 1 表示百分比（如 1.03 = 103%），需要 /100
            knock_out_pct = knock_out_raw / 100 if knock_out_raw > 1 else knock_out_raw
            first_ko = entry_price * knock_out_pct

        # 敲出百分比显示（如 1.03 显示为 103%）
        knock_out_pct_display = f"{knock_out_raw:.1f}%"

        # 敲出点位序列（后续月份递减）
        knock_out_pct = knock_out_raw / 100 if knock_out_raw > 1 else knock_out_raw
        ko_series = calc_knock_out_series(
            entry_price, knock_out_pct, lock_period, monthly_decrement
        )

        # 降落伞、票息等：原始值如 0.85 表示 85%
        parachute_display = f"{parachute * 100:.1f}%" if parachute > 0 else "无"
        monthly_coupon_display = f"{monthly_coupon * 100:.2f}%" if monthly_coupon > 0 else "无"
        tier1_display = f"{tier1 * 100:.2f}%" if tier1 > 0 else "无"
        tier2_display = f"{tier2 * 100:.2f}%" if tier2 > 0 else "不适用"
        tier3_display = f"{tier3 * 100:.2f}%" if tier3 > 0 else "不适用"
        dividend_display = f"{dividend:.4f}" if dividend > 0 else "无"
        margin_display = f"{margin * 100:.1f}%" if margin > 0 else "无"
        entry_display = format_wan_yuan(entry_price)

        return {
            "flight_no": str(name).strip(),
            "code": str(fields.get(F_CODE, "")),
            "structure_type": str(fields.get(F_STRUCTURE_TYPE, "")),
            "subscribe_date": str(fields.get(F_SUBSCRIBE_DATE, "")),
            "lock_period": lock_period,
            "term": term,
            "entry_price": entry_price,
            "entry_display": entry_display,
            "knock_out_pct": knock_out_pct,
            "knock_out_pct_display": knock_out_pct_display,
            "first_knock_out": first_ko,
            "first_knock_out_display": format_wan_yuan(first_ko),
            "ko_series": ko_series,
            "parachute": parachute,
            "parachute_display": parachute_display,
            "monthly_coupon": monthly_coupon,
            "monthly_coupon_display": monthly_coupon_display,
            "tier1_coupon": tier1,
            "tier1_coupon_display": tier1_display,
            "tier2_coupon": tier2,
            "tier2_coupon_display": tier2_display,
            "tier3_coupon": tier3,
            "tier3_coupon_display": tier3_display,
            "dividend_point": dividend,
            "dividend_display": dividend_display,
            "margin_ratio": margin,
            "margin_display": margin_display,
            "customer_count": customer_count,
            "monthly_decrement": monthly_decrement,
            "monthly_decrement_display": f"{monthly_decrement * 100:.2f}%",
        }
    except Exception as e:
        print(f"[WARN] Failed to parse product: {e}")
        return None


# =============================================================================
# 报告构建
# =============================================================================
def build_index_section(indices: List[Dict]) -> str:
    """构建指数行情文本"""
    if not indices:
        return "【指数行情】暂无数据"
    lines = ["【指数行情】"]
    for idx in indices:
        sign = "+" if idx["change"] >= 0 else ""
        lines.append(
            f"• {idx['name']}: {idx['current']:.2f} "
            f"{sign}{idx['change']:.2f} ({sign}{idx['change_pct']:.2f}%)"
        )
    return "\n".join(lines)


def build_product_section(products: List[Dict]) -> str:
    """构建产品列表文本"""
    if not products:
        return "【产品列表】暂无数据"

    lines = ["【产品列表】"]
    for p in products[:10]:
        lines.append(
            f"\n◆ {p['flight_no']}（{p['code']}）\n"
            f"  入场价 {p['entry_display']} | 敲出 {p['knock_out_pct_display']} | "
            f"首敲点位 {p['first_knock_out_display']}\n"
            f"  锁定期 {p['lock_period']}月 | 期限 {p['term']}月 | 降落伞 {p['parachute_display']}\n"
            f"  月票息 {p['monthly_coupon_display']} | "
            f"票息结构 {p['tier1_coupon_display']} / {p['tier2_coupon_display']} / {p['tier3_coupon_display']}"
        )

    if len(products) > 10:
        lines.append(f"\n...共 {len(products)} 只产品")
    return "\n".join(lines)


def build_daily_report() -> str:
    """构建每日收盘纯文本报告"""
    now = datetime.now()
    date_str = now.strftime("%Y年%m月%d日")

    indices = get_indices_batch(settings.indices_list)
    raw_products = query_product_table()
    products = [p for p in (parse_product_record(r) for r in raw_products) if p]

    index_section = build_index_section(indices)
    product_section = build_product_section(products)

    header = f"📊 【收盘简报】{date_str}\n\n"
    risk = (
        "\n---\n"
        "⚠️ 本报告仅供参考，不构成投资建议。\n\n"
        "私募基金投资具有较高风险，过往业绩不代表未来表现。"
    )

    return f"{header}{index_section}\n\n{product_section}{risk}"


# =============================================================================
# 飞书卡片构建
# =============================================================================
def build_product_card_elements(products: List[Dict]) -> List[dict]:
    """构建产品区域的卡片 elements"""
    elements = []

    if not products:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**【雪球结构产品】**\n暂无产品数据"}
        })
        return elements

    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": f"**【雪球结构产品】（共 {len(products)} 只）**"}
    })

    for p in products[:5]:
        # 敲出点位序列展示（取前3个）
        ko_lines = []
        for ko in p["ko_series"][:3]:
            ko_lines.append(f"  第{ko['month']}月: {format_wan_yuan(ko['knock_out_price'])}")
        ko_series_text = "\n".join(ko_lines) if ko_lines else "  无"

        content = (
            f"**◆ {p['flight_no']}** `{p['code']}`\n"
            f"结构: {p['structure_type']} | 期限: {p['term']}月 | "
            f"锁定期: {p['lock_period']}月 | 客户数: {p['customer_count']}\n"
            f"入场价: `{p['entry_display']}` | 敲出: `{p['knock_out_pct_display']}` | "
            f"保证金: `{p['margin_display']}`\n"
            f"首敲点位: `{p['first_knock_out_display']}`\n"
            f"敲出点位序列:\n{ko_series_text}\n"
            f"降落伞: `{p['parachute_display']}` | 派息点位: `{p['dividend_display']}`\n"
            f"月票息: `{p['monthly_coupon_display']}` | "
            f"票息结构: T1=`{p['tier1_coupon_display']}` / "
            f"T2=`{p['tier2_coupon_display']}` / T3=`{p['tier3_coupon_display']}`"
        )

        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": content}})
        elements.append({"tag": "hr"})

    if len(products) > 5:
        elements.append({
            "tag": "div",
            "text": {"tag": "plain_text", "content": f"...共 {len(products)} 只产品，显示前5只"}
        })

    return elements


def build_daily_report_card() -> dict:
    """构建飞书卡片消息"""
    now = datetime.now()
    date_str = now.strftime("%Y年%m月%d日")

    indices = get_indices_batch(settings.indices_list)
    raw_products = query_product_table()
    products = [p for p in (parse_product_record(r) for r in raw_products) if p]

    # 指数行情行
    index_elements = []
    for idx in indices:
        sign = "+" if idx["change"] >= 0 else ""
        emoji = "🔴" if idx["change"] < 0 else "🟢"
        index_elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"{emoji} **{idx['name']}** "
                    f"{idx['current']:.2f} {sign}{idx['change']:.2f} "
                    f"({sign}{idx['change_pct']:.2f}%)"
                ),
            },
        })

    product_elements = build_product_card_elements(products)

    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"📊 收盘简报 {date_str}"},
                "template": "red",
            },
            "elements": [
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": "**【指数行情】**"},
                },
                *index_elements,
                {"tag": "hr"},
                *product_elements,
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": (
                                "⚠️ 本报告仅供参考，不构成投资建议。"
                                "私募基金投资具有较高风险，过往业绩不代表未来表现。"
                            ),
                        }
                    ],
                },
            ],
        },
    }

    return card
