"""Embedding wrapper for PE knowledge base using local bge-m3 model"""
import os
import logging
from typing import List
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# HuggingFace cache home - default to user cache on Windows
os.environ.setdefault("HF_HOME", os.path.join(os.path.expanduser("~"), ".cache", "huggingface"))

# bge-m3 configuration
BGE_MODEL = os.getenv("BGE_MODEL", "BAAI/bge-m3")
BGE_DEVICE = os.getenv("BGE_DEVICE", "cpu")  # cpu or cuda

logger = logging.getLogger(__name__)


class BGEM3Embedder:
    """Local bge-m3 embedding model wrapper"""

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_model()
        return cls._instance

    def _load_model(self):
        """Load bge-m3 model on first use"""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading bge-m3 model: {BGE_MODEL} on {BGE_DEVICE}...")
            self._model = SentenceTransformer(
                BGE_MODEL,
                device=BGE_DEVICE,
                local_files_only=True,  # Force offline mode
            )
            logger.info("bge-m3 model loaded successfully")
        except ImportError:
            raise RuntimeError("sentence-transformers not installed. Run: pip install sentence-transformers")

    def encode(self, texts: List[str], batch_size: int = 8) -> List[List[float]]:
        """
        Generate embeddings for texts.

        Args:
            texts: List of text strings
            batch_size: Batch size for encoding

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        embeddings = self._model.encode(texts, batch_size=batch_size, convert_to_numpy=True)
        # Convert to list format
        if hasattr(embeddings, 'tolist'):
            embeddings = embeddings.tolist()
        return embeddings

    def encode_query(self, text: str) -> List[float]:
        """
        Generate embedding for a single query text.

        Args:
            text: Query text

        Returns:
            Embedding vector
        """
        embeddings = self.encode([text])
        return embeddings[0] if embeddings else []


# Global instance
_embedder = None


def get_embedder() -> BGEM3Embedder:
    """Get or create global embedder instance"""
    global _embedder
    if _embedder is None:
        _embedder = BGEM3Embedder()
    return _embedder


def embed_texts(texts: List[str], batch_size: int = 8) -> List[List[float]]:
    """
    Generate embeddings for a list of texts using bge-m3.

    Args:
        texts: List of text strings to embed
        batch_size: Batch size for encoding

    Returns:
        List of embedding vectors
    """
    embedder = get_embedder()
    return embedder.encode(texts, batch_size=batch_size)


def embed_query(text: str) -> List[float]:
    """
    Generate embedding for a single query text.

    Args:
        text: Query text to embed

    Returns:
        Embedding vector
    """
    embedder = get_embedder()
    return embedder.encode_query(text)


def get_embedding_dim() -> int:
    """Get embedding dimension for bge-m3"""
    return 1024


if __name__ == "__main__":
    # Quick test
    test_text = "私募基金的投资策略有哪些？"
    emb = embed_query(test_text)
    print(f"Embedding dim: {len(emb)}")
    print(f"First 5 values: {emb[:5]}")
