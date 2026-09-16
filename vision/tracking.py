import threading

from vision.yolo import get_yolo

_infer_lock = threading.Lock()  # model.track() carries internal tracker state across calls


def track_frame(frame):
    """Run detection+tracking on one BGR frame.

    Returns (annotated_frame, detections). detections keep a persistent
    `track_id` so the same person/object stays identified across frames.
    """
    if frame is None:
        raise ValueError("No camera frame given")
    model = get_yolo()
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
