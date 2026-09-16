from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

MAX_CHARS = 8000
TIMEOUT_SECONDS = 10


def fetch_page(url: str) -> str:
    parsed = urlparse(url or "")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("fetch_page only accepts http(s) URLs")

    resp = requests.get(
        url,
        timeout=TIMEOUT_SECONDS,
        headers={"User-Agent": "Mozilla/5.0 (compatible; JaviAssistant/1.0)"},
        allow_redirects=True,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return text[:MAX_CHARS]
