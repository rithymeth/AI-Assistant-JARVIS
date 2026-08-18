import threading
import time

import cv2

from tools.camera import read_frame
from vision.tracking import track_frame

DEFAULT_FPS = 8.0

_lock = threading.Lock()
_latest_detections: list[dict] = []


def get_latest_detections() -> list[dict]:
    with _lock:
        return list(_latest_detections)


def mjpeg_frames(fps: float = DEFAULT_FPS):
    """Generator of multipart/x-mixed-replace JPEG chunks — one detect+track
    pass per frame, boxes/labels/IDs burned in. Runs until the client
    disconnects (FastAPI's StreamingResponse stops pulling from a generator
    when the connection closes)."""
    interval = 1.0 / fps
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
            pass  # transient camera/inference error — skip this frame, keep streaming
        elapsed = time.monotonic() - start
        time.sleep(max(0.0, interval - elapsed))
