import uuid
from datetime import datetime, timezone

from core.memory.chroma_client import get_client, get_embedder

MEMORY_TYPE_CONVERSATION = "conversation_turn"
MAX_QUERY_CANDIDATES = 12
RECENCY_BONUS_WINDOW_DAYS = 14.0


def _collection():
    return get_client().get_or_create_collection("javi_memories")


def _dedupe_ranked_rows(rows: list[dict], k: int) -> list[str]:
    seen = set()
    docs = []
    for row in sorted(rows, key=lambda r: r["score"]):
        text = (row["document"] or "").strip()
        if not text:
            continue
        normalized = " ".join(text.lower().split())
        if normalized in seen:
            continue
        seen.add(normalized)
        docs.append(text)
        if len(docs) >= k:
            break
    return docs


def _score(distance: float | None, created_at_ts: float | None) -> float:
    distance = 0.0 if distance is None else float(distance)
    if not created_at_ts:
        return distance
    age_days = max(0.0, (datetime.now(timezone.utc).timestamp() - float(created_at_ts)) / 86400.0)
    freshness = max(0.0, 1.0 - min(age_days / RECENCY_BONUS_WINDOW_DAYS, 1.0))
    return distance - (freshness * 0.08)


def add_memory(session_id: str, text: str, memory_type: str = MEMORY_TYPE_CONVERSATION) -> None:
    embedding = get_embedder().encode(text).tolist()
    _collection().add(
        ids=[str(uuid.uuid4())],
        embeddings=[embedding],
        documents=[text],
        metadatas=[
            {
                "session_id": session_id,
                "memory_type": memory_type,
                "created_at_ts": datetime.now(timezone.utc).timestamp(),
            }
        ],
    )


def search_memories(
    session_id: str,
    query: str,
    k: int = 3,
    memory_type: str = MEMORY_TYPE_CONVERSATION,
) -> list[str]:
    collection = _collection()
    if collection.count() == 0:
        return []
    embedding = get_embedder().encode(query).tolist()
    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(max(k * 4, k), MAX_QUERY_CANDIDATES, collection.count()),
        where={"session_id": session_id, "memory_type": memory_type},
        include=["documents", "metadatas", "distances"],
    )
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    rows = []
    for idx, document in enumerate(docs):
        metadata = metas[idx] if idx < len(metas) else {}
        distance = distances[idx] if idx < len(distances) else None
        rows.append(
            {
                "document": document,
                "score": _score(distance, metadata.get("created_at_ts")),
            }
        )
    return _dedupe_ranked_rows(rows, k)
