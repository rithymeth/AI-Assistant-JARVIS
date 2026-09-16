from config.settings import BASE_DIR

_model = None


def _weights_path() -> str:
    local = BASE_DIR / "yolov8n.pt"
    if local.exists():
        return str(local)
    return "yolov8n.pt"


def _get_model():
    global _model
    if _model is None:
        from ultralytics import YOLO

        _model = YOLO(_weights_path())
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
