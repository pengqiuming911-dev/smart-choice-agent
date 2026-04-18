"""Step 5: Document Sync Pipeline - Tests"""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_chunker():
    """Test markdown chunking"""
    from rag_service.rag.chunker import split_markdown

    md = """# 主标题

这是第一段内容。

## 子标题1

这是子标题1的内容。

### 子子标题

这是更深层的内容。

## 子标题2

这是子标题2的内容。
"""
    chunks = split_markdown(md)
    assert len(chunks) > 0, "Should create at least one chunk"
    print(f"[PASS] Chunker: created {len(chunks)} chunks")
    for i, c in enumerate(chunks):
        print(f"  Chunk {i+1}: {c[:40]}...")


def test_block_parser():
    """Test block to markdown conversion"""
    from rag_service.feishu.block_parser import blocks_to_markdown

    blocks = [
        {
            "block_id": "b001",
            "block_type": "heading1",
            "children": ["b002"],
            "parent_id": None
        },
        {
            "block_id": "b002",
            "block_type": "text",
            "text_elements": [{"text_run": {"content": "测试文档"}}],
            "children": [],
            "parent_id": "b001"
        },
        {
            "block_id": "b003",
            "block_type": "paragraph",
            "children": ["b004"],
            "parent_id": None
        },
        {
            "block_id": "b004",
            "block_type": "text",
            "text_elements": [{"text_run": {"content": "这是正文内容。"}}],
            "children": [],
            "parent_id": "b003"
        },
    ]

    md = blocks_to_markdown(blocks)
    assert "#" in md, "Should contain heading"
    assert "测试文档" in md, "Should contain heading text"
    print(f"[PASS] Block parser: generated markdown")
    print(f"  {md[:100]}...")


def test_db_connection():
    """Test PostgreSQL connection"""
    from rag_service.models.db import get_stats

    stats = get_stats()
    assert "active_documents" in stats
    assert "total_chunks" in stats
    print(f"[PASS] DB connection OK")
    print(f"  Stats: {stats}")


def test_qdrant_connection():
    """Test Qdrant connection"""
    from rag_service.rag.vector_store import get_client, DEFAULT_COLLECTION

    client = get_client()
    collections = [c.name for c in client.get_collections().collections]
    assert DEFAULT_COLLECTION in collections
    print(f"[PASS] Qdrant connection OK")
    print(f"  Collections: {collections}")


def test_feishu_client_mock():
    """Test Feishu client with mocked data"""
    from rag_service.feishu.client import FeishuClient
    from rag_service.feishu.block_parser import blocks_to_markdown

    # Mock the HTTP responses
    with patch("httpx.post") as mock_post:
        mock_post.return_value.json.return_value = {
            "code": 0,
            "data": {"tenant_access_token": "mock_token_123"}
        }

        client = FeishuClient(app_id="mock", app_secret="mock")
        token = client.get_token()
        assert token == "mock_token_123"

    print("[PASS] Feishu client mock OK")


def test_sync_pipeline_dry_run():
    """Test sync pipeline with dry run (no actual API calls)"""
    from rag_service.sync.pipeline import SyncPipeline

    # Create pipeline with mocked feishu client
    pipeline = SyncPipeline()

    # Just verify pipeline can be created
    assert pipeline.stats["total"] == 0
    print("[PASS] SyncPipeline initialized OK")


if __name__ == "__main__":
    tests = [
        test_chunker,
        test_block_parser,
        test_db_connection,
        test_qdrant_connection,
        test_feishu_client_mock,
        test_sync_pipeline_dry_run,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")

    if failed > 0:
        sys.exit(1)
    else:
        print("\n[OK] All Step 5 tests passed!")
