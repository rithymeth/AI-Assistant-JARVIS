import os

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb
from sentence_transformers import SentenceTransformer

from config.settings import BASE_DIR

_CHROMA_DIR = str(BASE_DIR / "chroma_data")

# Shared across memory modules so the embedding model and the on-disk Chroma
# store are only opened/loaded once, not once per collection.
client = chromadb.PersistentClient(path=_CHROMA_DIR)
embedder = SentenceTransformer("all-MiniLM-L6-v2")
