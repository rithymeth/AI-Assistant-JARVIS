try:
    from duckduckgo_search import DDGS
except ImportError:  # package renamed to `ddgs` in later releases
    try:
        from ddgs import DDGS
    except ImportError:  # pragma: no cover
        DDGS = None


def web_search(query: str, max_results: int = 5) -> list[dict]:
    if not query or not str(query).strip():
        raise ValueError("Search query is required")
    if DDGS is None:
        raise RuntimeError("duckduckgo-search is not installed")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results) or [])
    except Exception as exc:
        raise RuntimeError(f"Web search failed: {exc}") from exc
    return [{"title": r.get("title"), "url": r.get("href"), "snippet": r.get("body")} for r in results]
