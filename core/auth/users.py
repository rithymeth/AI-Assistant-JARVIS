import hashlib
import secrets
from dataclasses import dataclass

from config.settings import CODE_ALPHABET, CODE_LENGTH

PBKDF2_ITERATIONS = 200_000


@dataclass(frozen=True)
class User:
    id: int
    username: str
    role: str  # "admin" | "standard"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


LOOPBACK_USER = User(id=0, username="local", role="admin")


def generate_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def hash_new_code(code: str) -> tuple[str, str]:
    code = (code or "").strip()
    if not code:
        raise ValueError("Access code can't be empty")
    salt = secrets.token_hex(16)
    return _pbkdf2(code, salt), salt


def verify_code(code: str, salt: str, code_hash: str) -> bool:
    if not code or not salt or not code_hash:
        return False
    return secrets.compare_digest(_pbkdf2(code, salt), code_hash)


def _pbkdf2(code: str, salt: str) -> str:
    normalized = code.strip().upper().encode()
    return hashlib.pbkdf2_hmac("sha256", normalized, salt.encode(), PBKDF2_ITERATIONS).hex()
