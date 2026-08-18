import threading

from ultralytics import YOLO

_model = None
_infer_lock = threading.Lock()  # model.track() carries internal tracker state across calls


def _get_model():
    global _model
    if _model is None:
        _model = YOLO("yolov8n.pt")
    return _model


def track_frame(frame):
    """Run detection+tracking on one BGR frame.

    Returns (annotated_frame, detections) — annotated_frame is the same frame
    with boxes/labels/track IDs drawn on it (via Ultralytics' own renderer,
    so styling matches its other outputs); detections is a JSON-friendly list
    with a persistent `track_id` per object so the same person/object keeps
    its identity across frames instead of just being re-labeled each time.
    """
    model = _get_model()
    with _infer_lock:
        results = model.track(frame, persist=True, verbose=False)
    result = results[0]

    detections = []
    if result.boxes is not None:
        for box in result.boxes:
            detections.append(
                {
                    "track_id": int(box.id[0]) if box.id is not None else None,
                    "label": result.names[int(box.cls[0])],
                    "confidence": round(float(box.conf[0]), 3),
                    "box": [round(v) for v in box.xyxy[0].tolist()],
                }
            )

    return result.plot(), detections
