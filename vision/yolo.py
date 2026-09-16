from config.settings import BASE_DIR

_model = None


def weights_path() -> str:
    local = BASE_DIR / "yolov8n.pt"
    if local.exists():
        return str(local)
    return "yolov8n.pt"


def get_yolo():
    """One shared YOLOv8 nano model for detect + track."""
    global _model
    if _model is None:
        from ultralytics import YOLO

        _model = YOLO(weights_path())
    return _model
