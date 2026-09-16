from collections.abc import Iterator

from config.settings import MODEL_NAME, OLLAMA_HOST, VISION_MODEL_NAME

_client = None


def _get_client():
    global _client
    if _client is None:
        from ollama import Client

        _client = Client(host=OLLAMA_HOST)
    return _client


def stream_chat(messages: list) -> Iterator[str]:
    try:
        chunks = _get_client().chat(model=MODEL_NAME, messages=messages, stream=True)
    except Exception as exc:
        yield f"I couldn't reach Ollama ({exc}). Is it running?"
        return
    for chunk in chunks:
        content = chunk.get("message", {}).get("content", "")
        if content:
            yield content


def chat_once(messages: list, tools: list | None = None):
    try:
        response = _get_client().chat(model=MODEL_NAME, messages=messages, tools=tools, stream=False)
    except Exception as exc:
        raise RuntimeError(f"Ollama chat failed: {exc}") from exc
    return response.message


def describe_image(image_path: str, prompt: str) -> str:
    if not image_path or not str(image_path).strip():
        raise ValueError("No image path given")
    prompt = (prompt or "").strip() or "Describe this image briefly."
    try:
        response = _get_client().chat(
            model=VISION_MODEL_NAME,
            messages=[{"role": "user", "content": prompt, "images": [str(image_path).strip()]}],
            stream=False,
        )
    except Exception as exc:
        raise RuntimeError(f"Vision model failed: {exc}") from exc
    return response.message.content


def is_available() -> bool:
    try:
        _get_client().list()
        return True
    except Exception:
        return False
