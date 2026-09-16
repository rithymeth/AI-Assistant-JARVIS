import threading

FACE_MATCH_THRESHOLD = 0.35
MIN_DET_SCORE = 0.65

_app = None
_app_lock = threading.Lock()


def _get_app():
    """Lazy singleton — buffalo_l is heavy, so load once."""
    global _app
    if _app is None:
        with _app_lock:
            if _app is None:
                from insightface.app import FaceAnalysis

                app = FaceAnalysis(name="buffalo_l")
                app.prepare(ctx_id=0, det_size=(640, 640))
                _app = app
    return _app


class NoFaceDetected(Exception):
    """No confident face in the image — retake the photo."""


def embed_face(image_path: str):
    if not image_path or not str(image_path).strip():
        raise NoFaceDetected("no image path given")
    import cv2

    img = cv2.imread(str(image_path).strip())
    if img is None:
        raise NoFaceDetected(f"could not read image: {image_path}")
    faces = [f for f in _get_app().get(img) if f.det_score >= MIN_DET_SCORE]
    if not faces:
        raise NoFaceDetected("no confident face detected in the image")
    best = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return best.embedding


def cosine_similarity(a, b) -> float:
    import numpy as np

    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return -1.0
    return float(np.dot(a, b) / (na * nb))


def best_match_score(embedding, enrolled: list) -> float:
    if not enrolled:
        return -1.0
    return max(cosine_similarity(embedding, e) for e in enrolled)


def is_match(embedding, enrolled: list) -> bool:
    return best_match_score(embedding, enrolled) >= FACE_MATCH_THRESHOLD
