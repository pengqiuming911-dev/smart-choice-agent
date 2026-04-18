"""Database operations for PE knowledge base"""
import os
import json
from typing import Optional, List
from datetime import datetime
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import Json, execute_values


POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    "postgresql://pekb:pekb_dev_password@localhost:5432/pekb"
)


@contextmanager
def get_connection():
    """Get database connection context manager"""
    conn = psycopg2.connect(POSTGRES_DSN)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_cursor():
    """Get database cursor context manager"""
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            cur.close()


# === Document operations ===

def upsert_document(
    document_id: str,
    space_id: str,
    obj_type: str,
    title: str,
    path: str,
    content_md: str,
    owner_id: str = None,
    last_edit_time: datetime = None,
    chunk_count: int = 0,
    status: str = "active",
) -> int:
    """
    Insert or update a document record.

    Returns:
        document db id
    """
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO documents (
                document_id, space_id, obj_type, title, path, content_md,
                owner_id, last_edit_time, chunk_count, status, synced_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (document_id) DO UPDATE SET
                title = EXCLUDED.title,
                path = EXCLUDED.path,
                content_md = EXCLUDED.content_md,
                owner_id = COALESCE(EXCLUDED.owner_id, documents.owner_id),
                last_edit_time = COALESCE(EXCLUDED.last_edit_time, documents.last_edit_time),
                chunk_count = EXCLUDED.chunk_count,
                status = EXCLUDED.status,
                synced_at = NOW()
            RETURNING id
        """, (
            document_id, space_id, obj_type, title, path, content_md,
            owner_id, last_edit_time, chunk_count, status
        ))
        result = cur.fetchone()
        return result[0] if result else None


def get_document(document_id: str) -> Optional[dict]:
    """Get document by document_id"""
    with get_cursor() as cur:
        cur.execute("""
            SELECT id, document_id, space_id, obj_type, title, path,
                   content_md, owner_id, last_edit_time, synced_at,
                   chunk_count, status
            FROM documents WHERE document_id = %s
        """, (document_id,))
        row = cur.fetchone()
        if row:
            return {
                "id": row[0],
                "document_id": row[1],
                "space_id": row[2],
                "obj_type": row[3],
                "title": row[4],
                "path": row[5],
                "content_md": row[6],
                "owner_id": row[7],
                "last_edit_time": row[8],
                "synced_at": row[9],
                "chunk_count": row[10],
                "status": row[11],
            }
        return None


def set_document_status(document_id: str, status: str) -> bool:
    """Update document status (active/deleted)"""
    with get_cursor() as cur:
        cur.execute("""
            UPDATE documents SET status = %s, synced_at = NOW()
            WHERE document_id = %s
        """, (status, document_id))
        return cur.rowcount > 0


# === Permission operations ===

def set_document_permissions(document_id: str, permissions: List[dict]) -> int:
    """
    Set permissions for a document (replaces existing).

    Args:
        document_id: Feishu document_id
        permissions: List of {"principal_type": "user"/"dept"/"tenant",
                               "principal_id": "...", "perm": "read"/"edit"}

    Returns:
        Number of permission records created
    """
    if not permissions:
        return 0

    with get_cursor() as cur:
        # Delete existing permissions
        cur.execute("""
            DELETE FROM document_permissions WHERE document_id = %s
        """, (document_id,))

        # Insert new permissions
        values = [
            (document_id, p["principal_type"], p["principal_id"], p.get("perm", "read"))
            for p in permissions
        ]
        execute_values(
            cur,
            """INSERT INTO document_permissions
               (document_id, principal_type, principal_id, perm)
               VALUES %s""",
            values,
        )
        return len(values)


def get_accessible_doc_ids(user_open_id: str, dept_id: str = None) -> List[str]:
    """
    Get list of document_ids that a user can access.

    Args:
        user_open_id: User's open_id
        dept_id: Optional department ID

    Returns:
        List of accessible document_ids
    """
    with get_cursor() as cur:
        # User has access if:
        # 1. They are directly granted permission
        # 2. Their department is granted permission
        # 3. Everyone (tenant) is granted permission
        cur.execute("""
            SELECT DISTINCT document_id FROM (
                SELECT document_id FROM document_permissions
                WHERE principal_type = 'user' AND principal_id = %s
                UNION
                SELECT document_id FROM document_permissions
                WHERE principal_type = 'dept' AND principal_id = %s
                UNION
                SELECT document_id FROM document_permissions
                WHERE principal_type = 'tenant'
            ) AS accessible
        """, (user_open_id, dept_id or ""))
        return [row[0] for row in cur.fetchall()]


# === Qualified investor operations ===

def is_qualified_investor(user_open_id: str) -> bool:
    """Check if user is in qualified investor whitelist"""
    with get_cursor() as cur:
        cur.execute("""
            SELECT 1 FROM qualified_investors
            WHERE user_open_id = %s
            AND (expire_at IS NULL OR expire_at > NOW())
        """, (user_open_id,))
        return cur.fetchone() is not None


def add_qualified_investor(
    user_open_id: str,
    name: str,
    level: str = "standard",
    expire_at: datetime = None,
) -> bool:
    """Add user to qualified investor whitelist"""
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO qualified_investors (user_open_id, name, verified_at, expire_at, level)
            VALUES (%s, %s, NOW(), %s, %s)
            ON CONFLICT (user_open_id) DO UPDATE SET
                name = EXCLUDED.name,
                expire_at = EXCLUDED.expire_at,
                level = EXCLUDED.level,
                verified_at = NOW()
        """, (user_open_id, name, expire_at, level))
        return True


# === Chat log operations ===

def insert_chat_log(
    session_id: str,
    user_open_id: str,
    user_name: str,
    question: str,
    answer: str,
    retrieved_chunks: list = None,
    citations: list = None,
    latency_ms: int = None,
    llm_model: str = None,
) -> int:
    """
    Insert a chat log entry for compliance auditing.

    Returns:
        log id
    """
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO chat_logs (
                session_id, user_open_id, user_name, question, answer,
                retrieved_chunks, citations, latency_ms, llm_model, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id
        """, (
            session_id, user_open_id, user_name, question, answer,
            Json(retrieved_chunks) if retrieved_chunks else None,
            Json(citations) if citations else None,
            latency_ms,
            llm_model,
        ))
        result = cur.fetchone()
        return result[0]


def get_chat_logs(
    user_open_id: str = None,
    limit: int = 100,
    offset: int = 0,
) -> List[dict]:
    """Get chat logs with optional user filter"""
    with get_cursor() as cur:
        if user_open_id:
            cur.execute("""
                SELECT id, session_id, user_open_id, user_name, question,
                       answer, retrieved_chunks, citations, latency_ms,
                       llm_model, created_at
                FROM chat_logs
                WHERE user_open_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (user_open_id, limit, offset))
        else:
            cur.execute("""
                SELECT id, session_id, user_open_id, user_name, question,
                       answer, retrieved_chunks, citations, latency_ms,
                       llm_model, created_at
                FROM chat_logs
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (limit, offset))

        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "session_id": r[1],
                "user_open_id": r[2],
                "user_name": r[3],
                "question": r[4],
                "answer": r[5],
                "retrieved_chunks": r[6],
                "citations": r[7],
                "latency_ms": r[8],
                "llm_model": r[9],
                "created_at": r[10],
            }
            for r in rows
        ]


# === Stats ===

def get_stats() -> dict:
    """Get basic sync stats"""
    with get_cursor() as cur:
        cur.execute("""
            SELECT
                (SELECT COUNT(*) FROM documents WHERE status = 'active') as active_docs,
                (SELECT SUM(chunk_count) FROM documents WHERE status = 'active') as total_chunks,
                (SELECT COUNT(*) FROM chat_logs WHERE created_at > NOW() - INTERVAL '24 hours') as daily_chats
        """)
        row = cur.fetchone()
        return {
            "active_documents": row[0] or 0,
            "total_chunks": row[1] or 0,
            "daily_chats": row[2] or 0,
        }
