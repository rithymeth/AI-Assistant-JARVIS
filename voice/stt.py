from faster_whisper import WhisperModel

_model = None


def _get_model():
    # CUDA requires the full CUDA/cuBLAS toolkit, not just a GPU driver, and
    # ctranslate2 only discovers a missing toolkit at first inference (not at
    # construction), so a try/except around WhisperModel() alone can't catch it.
    # CPU int8 is reliable everywhere and plenty fast for the "base" model.
    global _model
    if _model is None:
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str) -> str:
    model = _get_model()
    segments, _info = model.transcribe(audio_path)
    return " ".join(segment.text.strip() for segment in segments).strip()
