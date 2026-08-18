import os
import tempfile
import threading

import cv2

CAMERA_INDEX = 0
WARMUP_FRAMES = 3  # many webcams return a dark/stale first frame

# A single persistent capture, opened lazily on first use and kept open
# rather than opened/closed per call. DirectShow (cv2.CAP_DSHOW) generally
# only allows one open handle to a given webcam at a time on Windows, and
# live streaming (vision/camera_stream.py) needs continuous access — so
# every consumer (on-demand snapshot, background monitor, live stream,
# object tracking) shares this one handle via the lock-protected
# read_frame(), instead of each opening/closing its own.
_lock = threading.Lock()
_cap: cv2.VideoCapture | None = None


def _get_capture() -> cv2.VideoCapture:
    global _cap
    if _cap is None or not _cap.isOpened():
        _cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
        if not _cap.isOpened():
            raise RuntimeError("Could not open camera (index 0)")
        for _ in range(WARMUP_FRAMES):
            _cap.read()
    return _cap


def read_frame():
    """Grab one raw BGR frame (a numpy array) from the shared camera handle."""
    with _lock:
        cap = _get_capture()
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError("Failed to capture a frame from the camera")
        return frame


def capture_camera_frame() -> str:
    """Grab one frame and write it to a temp JPEG, returning the path."""
    frame = read_frame()
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    cv2.imwrite(path, frame)
    return path


def release_camera() -> None:
    global _cap
    with _lock:
        if _cap is not None:
            _cap.release()
            _cap = None
