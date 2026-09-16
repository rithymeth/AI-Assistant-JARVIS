try:
    from duckduckgo_search import DDGS
except ImportError:
    try:
        from ddgs import DDGS
    except ImportError:  # pragma: no cover
        DDGS = None

MAX_SEARCH_RESULTS = 10


def clamp_max_results(max_results: int | None) -> int:
    try:
        value = int(max_results) if max_results is not None else 5
    except (TypeError, ValueError):
        value = 5
    return max(1, min(value, MAX_SEARCH_RESULTS))


def web_search(query: str, max_results: int = 5) -> list[dict]:
    if not query or not str(query).strip():
        raise ValueError("Search query is required")
    if DDGS is None:
        raise RuntimeError("duckduckgo-search is not installed")
    max_results = clamp_max_results(max_results)
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(str(query).strip(), max_results=max_results) or [])
    except Exception as exc:
        raise RuntimeError(f"Web search failed: {exc}") from exc
    return [{"title": r.get("title"), "url": r.get("href"), "snippet": r.get("body")} for r in results]
