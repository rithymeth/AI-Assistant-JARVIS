import os

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str) -> str:
    path = (audio_path or "").strip()
    if not path:
        raise ValueError("No audio path given")
    if not os.path.exists(path):
        raise ValueError(f"Audio file not found: {path}")
    model = _get_model()
    segments, _info = model.transcribe(path)
    text = " ".join(segment.text.strip() for segment in segments).strip()
    return text or "(no speech detected)"
