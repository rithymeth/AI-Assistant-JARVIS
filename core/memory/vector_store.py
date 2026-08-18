import uuid

from core.memory.chroma_client import client, embedder

_collection = client.get_or_create_collection("javi_memories")


def add_memory(session_id: str, text: str) -> None:
    embedding = embedder.encode(text).tolist()
    _collection.add(
        ids=[str(uuid.uuid4())],
        embeddings=[embedding],
        documents=[text],
        metadatas=[{"session_id": session_id}],
    )


def search_memories(session_id: str, query: str, k: int = 3) -> list[str]:
    if _collection.count() == 0:
        return []
    embedding = embedder.encode(query).tolist()
    results = _collection.query(
        query_embeddings=[embedding],
        n_results=min(k, _collection.count()),
        where={"session_id": session_id},
    )
    return results.get("documents", [[]])[0]
