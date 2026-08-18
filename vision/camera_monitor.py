import os
import threading
from datetime import datetime, timezone

from core.brain.llm import describe_image
from tools.camera import capture_camera_frame

MONITOR_PROMPT = "Briefly describe what's visible in this webcam frame in one sentence."
DEFAULT_INTERVAL_S = 15.0

_lock = threading.Lock()
_thread: threading.Thread | None = None
_stop_event = threading.Event()
_state = {
    "active": False,
    "interval_s": DEFAULT_INTERVAL_S,
    "last_description": None,
    "last_capture_at": None,
    "started_at": None,
}


def _loop(interval_s: float) -> None:
    while not _stop_event.is_set():
        try:
            path = capture_camera_frame()
            try:
                desc = describe_image(path, MONITOR_PROMPT)
            finally:
                os.remove(path)
            with _lock:
                _state["last_description"] = desc
                _state["last_capture_at"] = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            with _lock:
                _state["last_description"] = f"[capture error: {e}]"
        _stop_event.wait(interval_s)


def start_monitor(interval_s: float = DEFAULT_INTERVAL_S) -> dict:
    global _thread
    with _lock:
        if _state["active"]:
            return dict(_state)
        _stop_event.clear()
        _state.update(
            active=True,
            interval_s=interval_s,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        _thread = threading.Thread(target=_loop, args=(interval_s,), daemon=True)
        _thread.start()
        return dict(_state)


def stop_monitor() -> dict:
    with _lock:
        if not _state["active"]:
            return dict(_state)
        _stop_event.set()
        _state["active"] = False
        return dict(_state)


def get_status() -> dict:
    with _lock:
        return dict(_state)
