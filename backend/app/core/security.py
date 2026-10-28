"""Security, Hashing, and Session Cryptography."""

import secrets
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import settings

# Initialize Argon2id password hasher with secure defaults
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB memory
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

# Serializer for signed session cookies
serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="campusiq-session-cookie")


def get_password_hash(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False


def create_session_token() -> str:
    """Generate a cryptographically secure random session token."""
    return secrets.token_urlsafe(32)


def sign_session_cookie(session_token: str) -> str:
    """Cryptographically sign a session token for secure cookie transmission."""
    return serializer.dumps(session_token)


def verify_session_cookie(signed_cookie: str, max_age: int = None) -> str | None:
    """Verify and unpack a signed session cookie. Returns token if valid, None if tampered/expired."""
    if max_age is None:
        max_age = settings.SESSION_MAX_AGE_SECONDS
    try:
        return serializer.loads(signed_cookie, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
