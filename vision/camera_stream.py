import threading
import time

from tools.camera import read_frame
from vision.tracking import track_frame

DEFAULT_FPS = 8.0
MIN_FPS = 1.0
MAX_FPS = 15.0

_lock = threading.Lock()
_latest_detections: list[dict] = []


def clamp_fps(fps: float | None) -> float:
    try:
        value = float(fps) if fps is not None else DEFAULT_FPS
    except (TypeError, ValueError):
        value = DEFAULT_FPS
    return max(MIN_FPS, min(value, MAX_FPS))


def get_latest_detections() -> list[dict]:
    with _lock:
        return list(_latest_detections)


def mjpeg_frames(fps: float = DEFAULT_FPS):
    import cv2

    interval = 1.0 / clamp_fps(fps)
    while True:
        start = time.monotonic()
        try:
            frame = read_frame()
            annotated, detections = track_frame(frame)
            with _lock:
                _latest_detections[:] = detections
            ok, buf = cv2.imencode(".jpg", annotated)
            if ok:
                yield (
                    b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                    + buf.tobytes()
                    + b"\r\n"
                )
        except Exception:
            pass
        elapsed = time.monotonic() - start
        time.sleep(max(0.0, interval - elapsed))
