from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

MAX_CHARS = 8000
MAX_BYTES = 2_000_000
TIMEOUT_SECONDS = 10


def _read_capped(resp: requests.Response) -> str:
    chunks: list[bytes] = []
    total = 0
    for chunk in resp.iter_content(65536):
        if not chunk:
            continue
        chunks.append(chunk)
        total += len(chunk)
        if total >= MAX_BYTES:
            break
    return b"".join(chunks).decode(resp.encoding or "utf-8", errors="replace")


def fetch_page(url: str) -> str:
    parsed = urlparse(url or "")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("fetch_page only accepts http(s) URLs")

    try:
        resp = requests.get(
            url,
            timeout=TIMEOUT_SECONDS,
            headers={"User-Agent": "Mozilla/5.0 (compatible; JaviAssistant/1.0)"},
            allow_redirects=True,
            stream=True,
        )
        resp.raise_for_status()
        html = _read_capped(resp)
    except requests.RequestException as exc:
        raise RuntimeError(f"Page fetch failed: {exc}") from exc
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return text[:MAX_CHARS]
