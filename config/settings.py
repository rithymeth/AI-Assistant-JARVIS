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

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2:3b")
VISION_MODEL_NAME = os.getenv("VISION_MODEL_NAME", "moondream")
PORT = int(os.getenv("PORT", "8000"))
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "javi.db"))


# Unambiguous on a phone screen/keyboard: no 0/O, 1/I/L, no punctuation
# (token_urlsafe's default alphabet includes '-'/'_', which is genuinely
# confusing to transcribe by hand — a real usability bug, not hypothetical).
# Public (no leading underscore): reused by core/auth/users.py to generate
# per-user codes with the same phone-friendly alphabet.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8


def _load_or_create_access_code() -> str:
    """Gates non-localhost (LAN) requests — see api/server.py's middleware.
    Requests from the machine itself never need this. Persisted to a local
    file so it stays stable across restarts instead of forcing a re-entry
    on your phone every time; set ACCESS_CODE in .env to pin your own.
    Comparison is case-insensitive (see api/server.py), so a phone
    keyboard's autocapitalize can't cause a false mismatch."""
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

# Optional: emails the access code + LAN URL on server startup so you can
# grab it from your phone without walking over to look at the terminal.
# All blank by default — the feature no-ops until you fill these in
# yourself directly in .env (never paste credentials into chat).
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", "")

# Optional default city for get_weather() when the user just says "what's
# the weather" without naming a place. Blank by default — the tool then
# requires a location be given each time rather than silently guessing one.
WEATHER_LOCATION = os.getenv("WEATHER_LOCATION", "")
