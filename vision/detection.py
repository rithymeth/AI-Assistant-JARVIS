from ultralytics import YOLO

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = YOLO("yolov8n.pt")
    return _model


def detect_objects(image_path: str) -> list[dict]:
    model = _get_model()
    results = model(image_path, verbose=False)
    detections = []
    for result in results:
        for box in result.boxes:
            detections.append(
                {
                    "label": result.names[int(box.cls[0])],
                    "confidence": round(float(box.conf[0]), 3),
                }
            )
    return detections
