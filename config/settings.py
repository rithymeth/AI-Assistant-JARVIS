import os
import secrets
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv():
        return False

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        return default


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2:3b")
VISION_MODEL_NAME = os.getenv("VISION_MODEL_NAME", "moondream")
PORT = env_int("PORT", 8000)
HOST = os.getenv("HOST", "0.0.0.0")
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "javi.db"))

CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8


def _load_or_create_access_code() -> str:
    env_code = os.getenv("ACCESS_CODE")
    if env_code:
        return env_code
    code_file = BASE_DIR / ".access_code"
    if code_file.exists():
        return code_file.read_text().strip()
    code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
    code_file.write_text(code)
    return code


ACCESS_CODE = _load_or_create_access_code()

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = env_int("SMTP_PORT", 587)
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", "")
WEATHER_LOCATION = os.getenv("WEATHER_LOCATION", "")
CAMERA_INDEX = env_int("CAMERA_INDEX", 0)
