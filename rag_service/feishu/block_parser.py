"""Convert Feishu block tree to Markdown"""
import re
from typing import Optional


# Feishu block type mapping (number -> string name)
BLOCK_TYPE_MAP = {
    1: "page",
    2: "heading1",
    3: "heading2",
    4: "heading3",
    5: "heading4",
    6: "heading5",
    7: "heading6",
    12: "text",
    13: "bullet",
    14: "ordered",
    15: "code",
    16: "quote",
    17: "table",
    18: "table_row",
    19: "table_cell",
    22: "image",
    23: "divider",
    27: "callout",
    28: "paragraph",
}

# Block type to Markdown conversion
BLOCK_HANDLERS = {}


def register_handler(block_type: str):
    """Decorator to register a block type handler"""
    def decorator(func):
        BLOCK_HANDLERS[block_type] = func
        return func
    return decorator


@register_handler("paragraph")
def handle_paragraph(block: dict, children: list) -> str:
    text = "".join(children)
    return text + "\n" if text.strip() else ""


@register_handler("heading1")
def handle_heading1(block: dict, children: list) -> str:
    text = "".join(children)
    return f"# {text}\n"


@register_handler("heading2")
def handle_heading2(block: dict, children: list) -> str:
    text = "".join(children)
    return f"## {text}\n"


@register_handler("heading3")
def handle_heading3(block: dict, children: list) -> str:
    text = "".join(children)
    return f"### {text}\n"


@register_handler("heading4")
def handle_heading4(block: dict, children: list) -> str:
    text = "".join(children)
    return f"#### {text}\n"


@register_handler("heading5")
def handle_heading5(block: dict, children: list) -> str:
    text = "".join(children)
    return f"##### {text}\n"


@register_handler("heading6")
def handle_heading6(block: dict, children: list) -> str:
    text = "".join(children)
    return f"###### {text}\n"


@register_handler("text")
def handle_text(block: dict, children: list) -> str:
    elements = block.get("text_elements", [])
    result = ""
    for elem in elements:
        if "text_run" in elem:
            result += elem["text_run"].get("content", "")
    return result


@register_handler("bullet")
def handle_bullet(block: dict, children: list) -> str:
    text = "".join(children)
    return f"- {text}\n"


@register_handler("ordered")
def handle_ordered(block: dict, children: list) -> str:
    text = "".join(children)
    return f"1. {text}\n"


@register_handler("code")
def handle_code(block: dict, children: list) -> str:
    text = "".join(children)
    lang = block.get("code", {}).get("language", "")
    return f"```{lang}\n{text}\n```\n"


@register_handler("quote")
def handle_quote(block: dict, children: list) -> str:
    text = "".join(children)
    return f"> {text}\n"


@register_handler("table")
def handle_table(block: dict, children: list) -> str:
    """Simplified table handling"""
    if not children:
        return ""

    # First row is header
    rows = [c for c in children if c.strip()]
    if not rows:
        return ""

    # Build markdown table
    result = ""
    for i, row in enumerate(rows):
        result += row
        if i == 0:
            # Header separator
            cols = row.count("|") - 1
            result += "|" + "|".join(["---"] * cols) + "\n"
    return result


@register_handler("table_row")
def handle_table_row(block: dict, children: list) -> str:
    cells = children if children else [""]
    return "|" + "|".join(cells) + "|\n"


@register_handler("table_cell")
def handle_table_cell(block: dict, children: list) -> str:
    return "".join(children)


@register_handler("image")
def handle_image(block: dict, children: list) -> str:
    return "[图片]\n"


@register_handler("divider")
def handle_divider(block: dict, children: list) -> str:
    return "---\n"


@register_handler("callout")
def handle_callout(block: dict, children: list) -> str:
    emoji = block.get("callout", {}).get("emoji_id", "💡")
    text = "".join(children)
    return f"> {emoji} {text}\n"


def extract_text_from_element(elem: dict) -> str:
    """Extract text from a text element"""
    if "text_run" in elem:
        return elem["text_run"].get("content", "")
    return ""


def parse_block(block: dict, context: dict = None) -> tuple:
    """
    Parse a single block and its children recursively.

    Returns:
        (markdown_str, heading_list)
        heading_list is list of ancestor headings for breadcrumb
    """
    raw_type = block.get("block_type", "")
    # Map numeric type to string if needed
    block_type = BLOCK_TYPE_MAP.get(raw_type, raw_type)
    block_id = block.get("block_id", "")

    # Get children blocks
    children_blocks = block.get("children", [])
    children_md = []
    child_headings = []

    for child_id in children_blocks:
        child_block = context.get(child_id) if context else None
        if child_block:
            child_md, _ = parse_block(child_block, context)
            children_md.append(child_md)

    # Find current heading level if this is a heading
    heading = ""
    if isinstance(block_type, str) and block_type.startswith("heading"):
        heading_text = "".join(children_md).strip()
        heading = heading_text

    # Get handler
    handler = BLOCK_HANDLERS.get(block_type)
    if handler:
        try:
            md = handler(block, children_md)
        except Exception as e:
            md = ""
    else:
        # Unknown block type, just concat children
        md = "".join(children_md)

    return md, heading


def blocks_to_markdown(blocks: list, root_block_id: str = None) -> str:
    """
    Convert Feishu block list to Markdown.

    Args:
        blocks: List of block dicts from Feishu API
        root_block_id: Optional root block ID to start from

    Returns:
        Markdown string
    """
    if not blocks:
        return ""

    # Build block lookup by ID
    block_map = {b.get("block_id", ""): b for b in blocks}

    # Find root blocks
    if root_block_id and root_block_id in block_map:
        root_blocks = [block_map[root_block_id]]
    else:
        # Find blocks with no parent (root level)
        root_blocks = []
        for b in blocks:
            parent_id = b.get("parent_id")
            if not parent_id or parent_id not in block_map:
                root_blocks.append(b)

    # Process each root block
    result_parts = []
    for block in root_blocks:
        md, _ = parse_block(block, block_map)
        result_parts.append(md)

    return "\n".join(result_parts)


def get_block_headings(blocks: list) -> list:
    """Extract all headings from blocks for breadcrumb generation"""
    headings = []

    for block in blocks:
        block_type = block.get("block_type", "")
        if block_type in ("heading1", "heading2", "heading3", "heading4", "heading5", "heading6"):
            # Get heading text
            children = block.get("children", [])
            text_parts = []
            for child_id in children:
                child = next((b for b in blocks if b.get("block_id") == child_id), None)
                if child and child.get("block_type") == "text":
                    for elem in child.get("text_elements", []):
                        if "text_run" in elem:
                            text_parts.append(elem["text_run"].get("content", ""))

            heading_text = "".join(text_parts).strip()
            level = int(block_type.replace("heading", ""))
            headings.append({"level": level, "text": heading_text})

    return headings


if __name__ == "__main__":
    # Quick test with sample blocks
    sample = [
        {
            "block_id": "b001",
            "block_type": "heading1",
            "children": ["b002"]
        },
        {
            "block_id": "b002",
            "block_type": "text",
            "text_elements": [
                {"text_run": {"content": "Hello World"}}
            ],
            "children": []
        }
    ]

    md = blocks_to_markdown(sample)
    print(md)
