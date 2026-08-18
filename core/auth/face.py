import threading

import cv2
import numpy as np
from insightface.app import FaceAnalysis

# Empirically calibrated (real captures via tools/camera.py — see the plan
# session's verification run): the same person, photographed twice a few
# seconds apart, scored ~0.69 cosine similarity; a different, known identity
# (insightface's own bundled Tom_Hanks_54745.png test asset) scored ~-0.08
# against the same captures. Set well below the observed same-person score
# (a real verification-time photo, taken under different lighting/pose than
# enrollment, will likely score lower than that same-second back-to-back
# pair) but with a wide margin above the different-person score — biased
# conservative on purpose, since this gates real control over the machine,
# not just a convenience check. Same rigor as the existing
# SEMANTIC_DEDUP_DISTANCE in core/memory/knowledge.py.
FACE_MATCH_THRESHOLD = 0.35

# Detections below this confidence are treated as noise, not a candidate
# face — caught directly during calibration: a real capture returned a
# second "face" at det_score 0.59 in a dim corner of the frame that wasn't
# actually a face on visual inspection.
MIN_DET_SCORE = 0.65

_app: FaceAnalysis | None = None
_app_lock = threading.Lock()


def _get_app() -> FaceAnalysis:
    """Lazy singleton — loading buffalo_l's five ONNX models takes real
    time, so it happens once (double-checked locking guards concurrent
    FastAPI requests hitting this before the first load finishes) rather
    than on every embed_face() call."""
    global _app
    if _app is None:
        with _app_lock:
            if _app is None:
                app = FaceAnalysis(name="buffalo_l")
                app.prepare(ctx_id=0, det_size=(640, 640))
                _app = app
    return _app


class NoFaceDetected(Exception):
    """Raised when no sufficiently confident face is found in an image —
    callers should treat this as "retake the photo", not "identity doesn't
    match"."""


def embed_face(image_path: str) -> np.ndarray:
    """512-d embedding of the most prominent confident face in the image
    (largest bounding box among detections at/above MIN_DET_SCORE — a real
    capture can trigger multiple low-confidence false-positive detections
    from background clutter, so this picks the one actual face)."""
    img = cv2.imread(image_path)
    if img is None:
        raise NoFaceDetected(f"could not read image: {image_path}")
    faces = [f for f in _get_app().get(img) if f.det_score >= MIN_DET_SCORE]
    if not faces:
        raise NoFaceDetected("no confident face detected in the image")
    best = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return best.embedding


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def best_match_score(embedding: np.ndarray, enrolled: list[np.ndarray]) -> float:
    """Max similarity against any of a user's enrolled embeddings — a user
    may enroll more than one photo (different angles/lighting), and
    matching any one of them is enough."""
    if not enrolled:
        return -1.0
    return max(cosine_similarity(embedding, e) for e in enrolled)


def is_match(embedding: np.ndarray, enrolled: list[np.ndarray]) -> bool:
    return best_match_score(embedding, enrolled) >= FACE_MATCH_THRESHOLD
