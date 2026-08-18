import hashlib
from datetime import datetime, timedelta, timezone

from core.memory.chroma_client import client, embedder

# Unlike vector_store.py's per-session conversation memory, this collection
# is global and durable — facts Javi has looked up (web searches, page
# reads, screen looks, file reads) persist across sessions, so it can draw
# on what it has learned before regardless of which browser session asks.
_collection = client.get_or_create_collection("javi_knowledge")

MAX_FACT_CHARS = 2000
DEFAULT_MAX_AGE_DAYS = 30

# Semantic dedup: if a NEW lookup's content is nearly identical (by vector
# distance) to an EXISTING entry stored under a different lookup key, reuse
# that entry's ID instead of creating a near-duplicate — catches the same
# fact looked up via differently-phrased queries.
#
# Calibrated empirically against this project's own embedder
# (all-MiniLM-L6-v2) on realistic tool-result content, not guessed:
#   - same fact, paraphrased query                     -> distance ~0.07
#   - same query, genuinely different result (page changed) -> distance ~0.42
#   - related but distinct facts (same topic)           -> distance ~0.49
#   - same fact, very different wording/verbosity        -> distance ~0.68
#   - unrelated facts                                    -> distance ~1.03
# The gap between "same fact, very different wording" (0.68) and "related
# but distinct" (0.49) is uncomfortably close for a small general-purpose
# embedder on this content shape — the model doesn't cleanly separate deep
# paraphrase from surface-level topical overlap. So the threshold is set
# conservatively low: it reliably catches close/obvious paraphrases and
# deliberately does NOT try to catch every semantically-equivalent-but-
# differently-worded case. Under-merging (a few near-duplicate entries
# survive) is a completeness limitation; over-merging (two distinct facts
# silently collapse into one, losing information) would be a correctness
# bug — the conservative threshold trades the former risk for avoiding
# the latter.
SEMANTIC_DEDUP_DISTANCE = 0.15


def _lookup_id(lookup_key: str) -> str:
    return hashlib.sha256(lookup_key.encode()).hexdigest()


def remember_fact(lookup_key: str, content: str) -> None:
    """lookup_key identifies a distinct thing looked up (e.g. a tool name +
    its args) — NOT the result content. Repeating the same lookup upserts
    (replaces) the prior entry rather than piling up duplicates, so a
    re-fetched page that changed keeps only its latest version, and an
    identical repeat lookup just refreshes its timestamp instead of
    growing the store. A different lookup whose content is nearly identical
    to an existing entry (see SEMANTIC_DEDUP_DISTANCE above) also merges
    into that entry rather than creating a near-duplicate."""
    content = content[:MAX_FACT_CHARS]
    embedding = embedder.encode(content).tolist()
    target_id = _lookup_id(lookup_key)

    if _collection.count() > 0:
        nearest = _collection.query(query_embeddings=[embedding], n_results=1)
        nearest_ids = nearest.get("ids", [[]])[0]
        nearest_distances = nearest.get("distances", [[]])[0]
        if nearest_ids and nearest_distances[0] < SEMANTIC_DEDUP_DISTANCE:
            target_id = nearest_ids[0]

    _collection.upsert(
        ids=[target_id],
        embeddings=[embedding],
        documents=[content],
        metadatas=[{"learned_at_ts": datetime.now(timezone.utc).timestamp()}],
    )


def recall_facts(query: str, k: int = 3, max_age_days: float = DEFAULT_MAX_AGE_DAYS) -> list[str]:
    if _collection.count() == 0:
        return []
    cutoff_ts = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).timestamp()
    embedding = embedder.encode(query).tolist()
    results = _collection.query(
        query_embeddings=[embedding],
        n_results=min(k, _collection.count()),
        where={"learned_at_ts": {"$gte": cutoff_ts}},
    )
    return results.get("documents", [[]])[0]
