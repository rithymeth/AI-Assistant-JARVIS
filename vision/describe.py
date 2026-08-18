from collections import Counter

from core.brain.llm import chat_once
from vision.detection import detect_objects
from vision.ocr import extract_text


def analyze_image(image_path: str) -> dict:
    detections = detect_objects(image_path)
    ocr_text = extract_text(image_path)

    counts = Counter(d["label"] for d in detections)
    objects_summary = ", ".join(f"{n}x {label}" for label, n in counts.items()) or "no recognizable objects"
    ocr_summary = ocr_text.strip() or "no text found"

    prompt = (
        "An image was analyzed with object detection and OCR. "
        f"Detected objects: {objects_summary}. "
        f"Text found in the image: {ocr_summary}. "
        "In 1-3 sentences, describe what this image likely shows, based only on this data."
    )
    response = chat_once([{"role": "user", "content": prompt}])

    return {
        "detections": detections,
        "ocr_text": ocr_text,
        "description": response.content,
    }
