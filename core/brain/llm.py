from collections.abc import Iterator

from ollama import Client, Message

from config.settings import MODEL_NAME, OLLAMA_HOST, VISION_MODEL_NAME

_client = Client(host=OLLAMA_HOST)


def stream_chat(messages: list) -> Iterator[str]:
    for chunk in _client.chat(model=MODEL_NAME, messages=messages, stream=True):
        content = chunk.get("message", {}).get("content", "")
        if content:
            yield content


def chat_once(messages: list, tools: list | None = None) -> Message:
    response = _client.chat(model=MODEL_NAME, messages=messages, tools=tools, stream=False)
    return response.message


def describe_image(image_path: str, prompt: str) -> str:
    response = _client.chat(
        model=VISION_MODEL_NAME,
        messages=[{"role": "user", "content": prompt, "images": [image_path]}],
        stream=False,
    )
    return response.message.content


def is_available() -> bool:
    try:
        _client.list()
        return True
    except Exception:
        return False
