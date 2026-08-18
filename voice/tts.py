import pyttsx3


def speak_to_file(text: str, out_path: str) -> None:
    engine = pyttsx3.init()
    engine.save_to_file(text, out_path)
    engine.runAndWait()
    engine.stop()
