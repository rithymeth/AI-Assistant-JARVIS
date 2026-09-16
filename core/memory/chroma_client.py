import os

from config.settings import BASE_DIR

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY_DISABLED", "1")

_CHROMA_DIR = str(BASE_DIR / "chroma_data")
_client = None
_embedder = None


def get_client():
    """Lazy-load the Chroma client so importing the app doesn't immediately
    pull in heavy ML dependencies during tests or lightweight code paths."""
    global _client
    if _client is None:
        import chromadb

        try:
            from chromadb.config import Settings

            _client = chromadb.PersistentClient(
                path=_CHROMA_DIR,
                settings=Settings(anonymized_telemetry=False),
            )
        except Exception:
            _client = chromadb.PersistentClient(path=_CHROMA_DIR)
    return _client


def get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder
