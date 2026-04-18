"""Markdown chunker for PE knowledge base documents"""
import re
from typing import List, Tuple

# Default chunk size in tokens (approximate)
DEFAULT_CHUNK_SIZE = 500
DEFAULT_OVERLAP = 80


def split_markdown(
    markdown: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> List[str]:
    """
    Split markdown into semantic chunks based on headings and token count.

    Strategy:
    1. First split by heading boundaries (H1/H2/H3)
    2. If a section exceeds chunk_size, split by paragraphs
    3. Add overlap between chunks for context preservation

    Args:
        markdown: Full markdown content
        chunk_size: Target tokens per chunk
        overlap: Overlap tokens between chunks

    Returns:
        List of chunk strings
    """
    if not markdown or not markdown.strip():
        return []

    # Split by heading boundaries
    heading_pattern = r"(?=^#{1,3}\s+.+$)"
    sections = re.split(heading_pattern, markdown, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip()]

    chunks = []
    current_chunk = []
    current_tokens = 0

    def add_chunk(text: str):
        nonlocal current_chunk, current_tokens
        if current_chunk:
            chunks.append("\n".join(current_chunk))
        current_chunk = [text]
        current_tokens = estimate_tokens(text)

    def estimate_tokens(text: str) -> int:
        # Rough estimate: ~2 chars per token for Chinese, ~4 for English
        chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
        other = len(text) - chinese
        return int(chinese / 2 + other / 4)

    for section in sections:
        section_tokens = estimate_tokens(section)

        if section_tokens <= chunk_size:
            # Section fits in one chunk
            if current_tokens + section_tokens <= chunk_size:
                current_chunk.append(section)
                current_tokens += section_tokens
            else:
                # Start new chunk
                add_chunk(section)
        else:
            # Section needs to be split
            if current_chunk:
                add_chunk(section)
            else:
                # Split by paragraphs
                paragraphs = section.split("\n\n")
                for para in paragraphs:
                    para_tokens = estimate_tokens(para)
                    if current_tokens + para_tokens <= chunk_size:
                        current_chunk.append(para)
                        current_tokens += para_tokens
                    else:
                        add_chunk(para)

    # Don't forget the last chunk
    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def get_heading_breadcrumb(markdown: str, position: int) -> List[str]:
    """
    Extract heading hierarchy before the given position.

    Args:
        markdown: Full markdown content
        position: Character position to get breadcrumb for

    Returns:
        List of heading texts from root to current section
    """
    before_text = markdown[:position]
    headings = re.findall(r"^(#{1,3})\s+(.+)$", before_text, re.MULTILINE)

    # Extract just the heading text (remove # markers)
    return [h[1].strip() for h in headings]


if __name__ == "__main__":
    # Quick test
    test_md = """# 主标题

这是第一段内容。

## 子标题1

这是子标题1的内容。

### 子子标题

这是更深层的内容。

## 子标题2

这是子标题2的内容。
"""
    chunks = split_markdown(test_md)
    print(f"Created {len(chunks)} chunks:")
    for i, c in enumerate(chunks):
        print(f"Chunk {i+1}: {c[:50]}...")
