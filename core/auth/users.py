import hashlib
import secrets
from dataclasses import dataclass

from config.settings import CODE_ALPHABET, CODE_LENGTH

# Deliberately high for an offline pbkdf2_hmac hash (no bcrypt/argon2 dependency
# needed) — codes are short (8 chars from a 32-symbol alphabet), so the work
# factor matters more than it would for a long random password.
PBKDF2_ITERATIONS = 200_000


@dataclass(frozen=True)
class User:
    id: int
    username: str
    role: str  # "admin" | "standard"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


# The person at the keyboard (loopback request) already had full control
# before any of this existed — that invariant doesn't change here, it's just
# now represented as an explicit synthetic admin user instead of an implicit
# bypass. id=0 never collides with a real autoincrement users.id (starts at 1).
LOOPBACK_USER = User(id=0, username="local", role="admin")


def generate_code() -> str:
    """Same phone-friendly alphabet as the original single-user ACCESS_CODE
    (config.settings) — no 0/O/1/I/L, no punctuation."""
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def hash_new_code(code: str) -> tuple[str, str]:
    """Returns (code_hash, code_salt) for storing a freshly generated code."""
    salt = secrets.token_hex(16)
    return _pbkdf2(code, salt), salt


def verify_code(code: str, salt: str, code_hash: str) -> bool:
    return secrets.compare_digest(_pbkdf2(code, salt), code_hash)


def _pbkdf2(code: str, salt: str) -> str:
    # Case-insensitive + trimmed, matching the existing global ACCESS_CODE
    # comparison — a phone keyboard's autocapitalize shouldn't be able to
    # turn a correctly-read per-user code into a mismatch either.
    normalized = code.strip().upper().encode()
    return hashlib.pbkdf2_hmac("sha256", normalized, salt.encode(), PBKDF2_ITERATIONS).hex()
