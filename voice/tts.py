def speak_to_file(text: str, out_path: str) -> None:
    text = (text or "").strip()
    if not text:
        raise ValueError("Nothing to speak")
    import pyttsx3

    engine = pyttsx3.init()
    engine.save_to_file(text, out_path)
    engine.runAndWait()
    engine.stop()
