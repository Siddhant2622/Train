from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the given plain-text password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a short-lived JWT access token.

    Args:
        subject: The user identifier (email or UUID) to embed in the 'sub' claim.
        extra_claims: Optional dict of additional claims (e.g. {"role": "admin"}).

    Returns:
        Encoded JWT string.
    """
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
        **(extra_claims or {}),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    """Create a long-lived JWT refresh token."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Raises:
        JWTError: If the token is invalid, expired, or tampered.

    Returns:
        The decoded payload dict.
    """
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def get_subject_from_token(token: str, token_type: str = "access") -> str:
    """Extract and return the 'sub' claim from a validated token.

    Args:
        token: Raw JWT string.
        token_type: Expected 'type' claim — "access" or "refresh".

    Raises:
        JWTError: If validation fails or token type doesn't match.

    Returns:
        The subject string (user email/UUID).
    """
    payload = decode_token(token)
    if payload.get("type") != token_type:
        raise JWTError(f"Expected token type '{token_type}', got '{payload.get('type')}'")
    sub = payload.get("sub")
    if sub is None:
        raise JWTError("Token missing 'sub' claim")
    return str(sub)
