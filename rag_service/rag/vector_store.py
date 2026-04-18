"""Qdrant vector store wrapper for PE knowledge base"""
import os
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import ResponseHandlingException

# Default configuration
DEFAULT_COLLECTION = os.getenv("QDRANT_COLLECTION", "pe_kb_chunks")
DEFAULT_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))


def get_client(url: str = None) -> QdrantClient:
    """Get Qdrant client instance"""
    if url is None:
        url = os.getenv("QDRANT_URL", "http://localhost:6333")
    return QdrantClient(url=url)


def ensure_collection(
    collection_name: str = DEFAULT_COLLECTION,
    vector_dim: int = DEFAULT_DIM,
    qdrant_url: str = None,
    recreate: bool = False,
) -> bool:
    """
    Ensure Qdrant collection exists with proper schema.

    Args:
        collection_name: Name of the collection
        vector_dim: Vector dimension (1024 for text-embedding-v3)
        qdrant_url: Qdrant server URL
        recreate: If True, delete and recreate the collection

    Returns:
        True if collection was created or already exists
    """
    client = get_client(qdrant_url)

    # Check if collection exists
    try:
        existing = client.get_collection(collection_name)
        if existing and not recreate:
            print(f"Collection '{collection_name}' already exists")
            return True
        elif recreate:
            client.delete_collection(collection_name)
            print(f"Deleted existing collection '{collection_name}'")
    except (ResponseHandlingException, Exception):
        pass

    # Create collection with proper schema
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=vector_dim,
            distance=models.Distance.COSINE,
        ),
    )
    # Create payload indexes separately
    client.create_payload_index(
        collection_name=collection_name,
        field_name="document_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    client.create_payload_index(
        collection_name=collection_name,
        field_name="space_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    print(f"Created collection '{collection_name}' with dim={vector_dim}")
    return True


def delete_collection(collection_name: str = DEFAULT_COLLECTION, qdrant_url: str = None) -> bool:
    """Delete a collection"""
    client = get_client(qdrant_url)
    try:
        client.delete_collection(collection_name)
        print(f"Deleted collection '{collection_name}'")
        return True
    except Exception as e:
        print(f"Error deleting collection: {e}")
        return False


if __name__ == "__main__":
    import sys

    action = sys.argv[1] if len(sys.argv) > 1 else "ensure"

    if action == "ensure":
        ensure_collection()
    elif action == "delete":
        delete_collection()
    elif action == "recreate":
        ensure_collection(recreate=True)
    else:
        print(f"Unknown action: {action}")
        print("Usage: python vector_store.py [ensure|delete|recreate]")
