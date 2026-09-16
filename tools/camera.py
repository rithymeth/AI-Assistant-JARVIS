import os
import tempfile
import threading

from config.settings import CAMERA_INDEX
from tools._platform import IS_WINDOWS

WARMUP_FRAMES = 3  # many webcams return a dark/stale first frame

# CAP_DSHOW = 700, CAP_ANY = 0. Avoid importing cv2 at module load so
# unit tests can inspect the backend choice without OpenCV installed.
CAP_DSHOW = 700
CAP_ANY = 0

_lock = threading.Lock()
_cap = None


def camera_backend() -> int:
    """DirectShow on Windows; default backend elsewhere (V4L2/AVFoundation)."""
    return CAP_DSHOW if IS_WINDOWS else CAP_ANY


def _open_capture():
    import cv2

    cap = cv2.VideoCapture(int(CAMERA_INDEX), camera_backend())
    if not cap.isOpened() and IS_WINDOWS:
        cap = cv2.VideoCapture(int(CAMERA_INDEX))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera (index {CAMERA_INDEX})")
    for _ in range(WARMUP_FRAMES):
        cap.read()
    return cap


def _get_capture():
    global _cap
    if _cap is None or not _cap.isOpened():
        _cap = _open_capture()
    return _cap


def read_frame():
    """Grab one raw BGR frame from the shared camera handle."""
    with _lock:
        cap = _get_capture()
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError("Failed to capture a frame from the camera")
        return frame


def capture_camera_frame() -> str:
    """Grab one frame and write it to a temp JPEG, returning the path."""
    import cv2

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
