import hashlib
from datetime import datetime, timedelta, timezone

from core.memory.chroma_client import get_client, get_embedder

MAX_FACT_CHARS = 2000
DEFAULT_MAX_AGE_DAYS = 30
FACT_TYPE_TOOL_LOOKUP = "tool_lookup"
MAX_QUERY_CANDIDATES = 12
RECENCY_BONUS_WINDOW_DAYS = 30.0
SEMANTIC_DEDUP_DISTANCE = 0.15


def _collection():
    return get_client().get_or_create_collection("javi_knowledge")


def _lookup_id(lookup_key: str) -> str:
    return hashlib.sha256(lookup_key.encode()).hexdigest()


def _score(distance: float | None, learned_at_ts: float | None) -> float:
    distance = 0.0 if distance is None else float(distance)
    if not learned_at_ts:
        return distance
    age_days = max(0.0, (datetime.now(timezone.utc).timestamp() - float(learned_at_ts)) / 86400.0)
    freshness = max(0.0, 1.0 - min(age_days / RECENCY_BONUS_WINDOW_DAYS, 1.0))
    return distance - (freshness * 0.08)


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


def _embedding_for(text: str) -> list[float]:
    vector = get_embedder().encode(text)
    return vector.tolist() if hasattr(vector, "tolist") else list(vector)


def remember_fact(lookup_key: str, content: str, fact_type: str = FACT_TYPE_TOOL_LOOKUP) -> None:
    lookup_key = (lookup_key or "").strip()
    content = (content or "").strip()
    if not lookup_key or not content:
        return
    content = content[:MAX_FACT_CHARS]
    embedding = _embedding_for(content)
    target_id = _lookup_id(lookup_key)
    collection = _collection()

    if collection.count() > 0:
        nearest = collection.query(
            query_embeddings=[embedding],
            n_results=1,
            where={"fact_type": fact_type},
            include=["distances"],
        )
        nearest_ids = nearest.get("ids", [[]])[0]
        nearest_distances = nearest.get("distances", [[]])[0]
        if nearest_ids and nearest_distances[0] < SEMANTIC_DEDUP_DISTANCE:
            target_id = nearest_ids[0]

    collection.upsert(
        ids=[target_id],
        embeddings=[embedding],
        documents=[content],
        metadatas=[
            {
                "learned_at_ts": datetime.now(timezone.utc).timestamp(),
                "fact_type": fact_type,
            }
        ],
    )


def recall_facts(
    query: str,
    k: int = 3,
    max_age_days: float = DEFAULT_MAX_AGE_DAYS,
    fact_type: str = FACT_TYPE_TOOL_LOOKUP,
) -> list[str]:
    query = (query or "").strip()
    if not query:
        return []
    collection = _collection()
    if collection.count() == 0:
        return []
    cutoff_ts = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).timestamp()
    embedding = _embedding_for(query)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(max(k * 4, k), MAX_QUERY_CANDIDATES, collection.count()),
        where={"learned_at_ts": {"$gte": cutoff_ts}, "fact_type": fact_type},
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
                "score": _score(distance, metadata.get("learned_at_ts")),
            }
        )
    return _dedupe_ranked_rows(rows, k)
