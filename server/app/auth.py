"""Authentication helpers: password hashing, JWT issuing, and the
``get_current_user`` dependency used to protect routes."""
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.models.user import User

# auto_error=False so we can raise a consistent 401 (instead of HTTPBearer's 403)
# when the Authorization header is missing.
bearer_scheme = HTTPBearer(auto_error=False)

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def _password_bytes(password: str) -> bytes:
    """Encode a password to bytes, truncated to bcrypt's 72-byte limit."""
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(_password_bytes(password), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    """Issue a signed JWT whose ``sub`` claim is the user id, expiring per config."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "iat": now, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate the Bearer token and return the authenticated ``User``."""
    if not settings.jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET is not configured",
        )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _CREDENTIALS_EXCEPTION

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        subject = payload.get("sub")
        if subject is None:
            raise _CREDENTIALS_EXCEPTION
        user_id = int(subject)
    except (JWTError, ValueError):
        raise _CREDENTIALS_EXCEPTION

    user = db.get(User, user_id)
    if user is None:
        raise _CREDENTIALS_EXCEPTION
    return user
