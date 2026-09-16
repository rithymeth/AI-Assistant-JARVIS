from vision.yolo import get_yolo


def detect_objects(image_path: str) -> list[dict]:
    if not image_path or not str(image_path).strip():
        raise ValueError("No image path given")
    model = get_yolo()
    results = model(str(image_path).strip(), verbose=False)
    detections = []
    for result in results:
        if result.boxes is None:
            continue
        for box in result.boxes:
            detections.append(
                {
                    "label": result.names[int(box.cls[0])],
                    "confidence": round(float(box.conf[0]), 3),
                }
            )
    return detections
