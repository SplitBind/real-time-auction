# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from real_time_auction.config import settings

# Explicitly register Argon2 and Bcrypt hashers to handle legacy bcrypt hashes seamlessly
password_hash = PasswordHash(
    hashers=[
        Argon2Hasher(),
        BcryptHasher(),
    ]
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a raw password against its stored hash."""
    try:
        return password_hash.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Generate a password hash."""
    return password_hash.hash(password)


def create_access_token(
    subject: Union[str, int],
    is_admin: bool = False,
    expires_delta: timedelta | None = None
) -> str:
    """Generate a signed JWT access token containing the user ID and admin flag."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "is_admin": is_admin,
        "exp": expire,
    }
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt
