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
    for chunk in _get_client().chat(model=MODEL_NAME, messages=messages, stream=True):
        content = chunk.get("message", {}).get("content", "")
        if content:
            yield content


def chat_once(messages: list, tools: list | None = None):
    response = _get_client().chat(model=MODEL_NAME, messages=messages, tools=tools, stream=False)
    return response.message


def describe_image(image_path: str, prompt: str) -> str:
    response = _get_client().chat(
        model=VISION_MODEL_NAME,
        messages=[{"role": "user", "content": prompt, "images": [image_path]}],
        stream=False,
    )
    return response.message.content


def is_available() -> bool:
    try:
        _get_client().list()
        return True
    except Exception:
        return False
