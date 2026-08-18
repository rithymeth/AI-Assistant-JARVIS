import threading
import time

import requests
import uvicorn
import webview

from api.server import app
from config.settings import PORT

# Cold-start imports alone (chromadb, sentence-transformers, ultralytics,
# easyocr — api.server's full dependency chain) measured ~17s on this
# machine before the server even starts binding; 15s was cutting it too
# close and could raise the RuntimeError below before the server ever had
# a real chance to come up. 45s gives comfortable margin for a slower cold
# boot (e.g. disk contention from other apps also starting at login).
STARTUP_TIMEOUT_SECONDS = 45


def _run_server():
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


def _wait_for_server(timeout=STARTUP_TIMEOUT_SECONDS) -> bool:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{PORT}/health"
    while time.time() < deadline:
        try:
            if requests.get(url, timeout=1).ok:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.3)
    return False


if __name__ == "__main__":
    threading.Thread(target=_run_server, daemon=True).start()
    if not _wait_for_server():
        raise RuntimeError(f"Javi's server didn't come up within {STARTUP_TIMEOUT_SECONDS}s")

    webview.create_window(
        "Javi",
        f"http://127.0.0.1:{PORT}",
        width=480,
        height=780,
        resizable=True,
        background_color="#000000",
    )
    webview.start()
