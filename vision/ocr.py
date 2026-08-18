import easyocr

_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader


def extract_text(image_path: str) -> str:
    reader = _get_reader()
    results = reader.readtext(image_path, detail=0)
    return "\n".join(results)
