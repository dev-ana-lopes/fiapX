from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fiapx_api.config import get_settings
from fiapx_api.db import get_session
from fiapx_api.models import User

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
