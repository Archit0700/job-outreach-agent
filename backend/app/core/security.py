"""Auth helpers: JWT sessions and Fernet token encryption."""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 72


def create_access_token(subject: str, extra: Optional[dict] = None) -> str:
    settings = get_settings()
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.app_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.app_secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None


def _fernet() -> Fernet:
    settings = get_settings()
    key = settings.token_encryption_key
    if not key or len(key) < 32:
        # Deterministic fallback for local/dev only — NOT for production
        key = Fernet.generate_key().decode() if False else "dGVzdC1rZXktZm9yLWxvY2FsLWRldi1vbmx5LW9rITI="
        # Use a fixed valid Fernet key for dev
        key = Fernet.generate_key()
        # Stable key derived from secret for consistency across restarts in same process
        import base64
        import hashlib

        digest = hashlib.sha256(settings.app_secret_key.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    else:
        key = key.encode() if isinstance(key, str) else key
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        raise ValueError("Failed to decrypt secret") from e
