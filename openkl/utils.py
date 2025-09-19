"""
Utility functions for OpenKL.
"""

import hashlib
from pathlib import Path

import numpy as np

# Global embedding model (lazy loaded)
_embedding_model = None


def get_embedding_model():
    """Get the embedding model, loading it if needed."""
    global _embedding_model
    if _embedding_model is None:
        from fastembed import TextEmbedding

        _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _embedding_model


def get_embedding(text: str) -> np.ndarray:
    """Get embedding vector for text."""
    model = get_embedding_model()
    # FastEmbed returns a generator, so we need to get the first result
    embeddings = list(model.embed([text]))
    return embeddings[0]


def chunk_text(text: str, chunk_size: int = 512, stride: int = 128) -> list[str]:
    """Split text into overlapping chunks."""
    # Simple word-based chunking
    words = text.split()
    chunks = []

    for i in range(0, len(words), stride):
        chunk_words = words[i : i + chunk_size]
        if chunk_words:
            chunk_text = " ".join(chunk_words)
            chunks.append(chunk_text)

            # Stop if we've covered all words
            if i + chunk_size >= len(words):
                break

    return chunks


def get_openkl_dir() -> Path:
    """Get the OpenKL directory path."""
    return Path.home() / ".ok"


def ensure_dir(path: Path):
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def get_content_hash(content: str) -> str:
    """Get SHA256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def format_timestamp(timestamp: str) -> str:
    """Format timestamp for display."""
    try:
        from datetime import datetime

        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return timestamp
