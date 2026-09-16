import os
import tempfile
import threading

from config.settings import CAMERA_INDEX
from tools._platform import IS_WINDOWS

WARMUP_FRAMES = 3
CAP_DSHOW = 700
CAP_ANY = 0

_lock = threading.Lock()
_cap = None


def camera_backend() -> int:
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
    with _lock:
        cap = _get_capture()
        ok, frame = cap.read()
        if not ok or frame is None:
            raise RuntimeError("Failed to capture a frame from the camera")
        return frame


def capture_camera_frame() -> str:
    import cv2

    frame = read_frame()
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    if not cv2.imwrite(path, frame) or not os.path.exists(path) or os.path.getsize(path) == 0:
        if os.path.exists(path):
            os.remove(path)
        raise RuntimeError("Camera captured an empty frame")
    return path


def release_camera() -> None:
    global _cap
    with _lock:
        if _cap is not None:
            _cap.release()
            _cap = None
