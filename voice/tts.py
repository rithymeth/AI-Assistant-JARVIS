def speak_to_file(text: str, out_path: str) -> None:
    text = (text or "").strip()
    if not text:
        raise ValueError("Nothing to speak")
    if not out_path or not str(out_path).strip():
        raise ValueError("No output path given")
    import pyttsx3

    engine = pyttsx3.init()
    engine.save_to_file(text, str(out_path).strip())
    engine.runAndWait()
    engine.stop()
