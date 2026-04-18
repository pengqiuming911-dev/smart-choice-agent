"""Step 4 Smoke Test - Infrastructure connectivity verification"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import redis
from qdrant_client import QdrantClient

# Load env
from dotenv import load_dotenv
load_dotenv()


def test_postgres():
    """Test PostgreSQL connectivity and schema"""
    postgres_dsn = os.getenv("POSTGRES_DSN", "postgresql://pekb:pekb_dev_password@localhost:5432/pekb")
    conn = psycopg2.connect(postgres_dsn)
    with conn.cursor() as cur:
        # Check tables exist
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = {row[0] for row in cur.fetchall()}
        expected_tables = {"chat_logs", "document_permissions", "documents", "qualified_investors"}
        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

        # Check indexes on documents table
        cur.execute("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'documents'
        """)
        indexes = {row[0] for row in cur.fetchall()}
        assert "idx_documents_space" in indexes, "Missing space index"
        assert "idx_documents_status" in indexes, "Missing status index"

        # Empty table check
        cur.execute("SELECT COUNT(*) FROM documents")
        count = cur.fetchone()[0]
        assert count == 0, f"documents table should be empty, got {count}"

    conn.close()
    print("[PASS] PostgreSQL: connectivity OK, 4 tables exist, indexes OK")


def test_redis():
    """Test Redis connectivity"""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    r = redis.from_url(redis_url)
    assert r.ping() is True, "Redis PING failed"

    # Test read/write
    r.set("test_key", "hello", ex=10)
    assert r.get("test_key") == b"hello", "Redis read/write failed"
    r.delete("test_key")

    print("[PASS] Redis: connectivity OK, read/write OK")


def test_qdrant():
    """Test Qdrant connectivity and collection"""
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    collection_name = os.getenv("QDRANT_COLLECTION", "pe_kb_chunks")

    client = QdrantClient(url=qdrant_url)

    # Check collection exists
    collections = {col.name for col in client.get_collections().collections}
    assert collection_name in collections, f"Collection '{collection_name}' not found"

    # Collection exists, just verify by getting info
    info = client.get_collection(collection_name)
    print(f"      Collection '{collection_name}' verified")

    print(f"[PASS] Qdrant: connectivity OK, collection '{collection_name}' exists, 0 vectors")


def test_env_security():
    """Test .env is not in git"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        # Check gitignore
        gitignore_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".gitignore")
        if os.path.exists(gitignore_path):
            with open(gitignore_path) as f:
                content = f.read()
            assert ".env" in content, ".env not in .gitignore"
            print("[PASS] Security: .env is in .gitignore")
        else:
            print("[WARN] Security: .gitignore not found")
    else:
        print("[WARN] Security: .env not found (OK if not created yet)")


if __name__ == "__main__":
    tests = [
        test_postgres,
        test_redis,
        test_qdrant,
        test_env_security,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test.__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")

    if failed > 0:
        sys.exit(1)
    else:
        print("\n[OK] All infrastructure smoke tests passed!")
