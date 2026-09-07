import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .db import get_session
from .models import AuthSession, User

bearer = HTTPBearer(auto_error=False)
password_hasher = PasswordHasher()


def make_token(user_id: UUID, token_type: str = "access") -> str:
    settings = get_settings()
    expiry = datetime.now(UTC) + (
        timedelta(minutes=settings.access_token_expire_minutes)
        if token_type == "access"
        else timedelta(days=settings.refresh_token_expire_days)
    )
    return jwt.encode(
        {"sub": str(user_id), "type": token_type, "exp": expiry},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def create_refresh_session(session: AsyncSession, user_id: UUID) -> tuple[str, AuthSession]:
    token = new_refresh_token()
    record = AuthSession(
        user_id=user_id,
        token_hash=hash_refresh_token(token),
        expires_at=datetime.now(UTC) + timedelta(days=get_settings().refresh_token_expire_days),
    )
    session.add(record)
    await session.flush()
    return token, record


def _user_id(token: str) -> UUID:
    try:
        payload = jwt.decode(
            token, get_settings().jwt_secret, algorithms=[get_settings().jwt_algorithm]
        )
        if payload.get("type") != "access":
            raise ValueError
        return UUID(str(payload["sub"]))
    except (ValueError, KeyError, jwt.PyJWTError) as exc:
        raise HTTPException(401, "invalid token") from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "authentication required")
    user = await session.get(User, _user_id(credentials.credentials))
    if user is None:
        raise HTTPException(401, "authentication required")
    return user


def password_hash(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return password_hasher.verify(encoded, password)
    except VerifyMismatchError:
        return False


async def find_user(session: AsyncSession, email: str) -> User | None:
    return (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
