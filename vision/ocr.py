_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        import easyocr

        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader


def extract_text(image_path: str) -> str:
    if not image_path or not str(image_path).strip():
        raise ValueError("No image path given")
    reader = _get_reader()
    results = reader.readtext(str(image_path).strip(), detail=0)
    text = "\n".join(str(item) for item in (results or [])).strip()
    return text or "(no text detected)"
