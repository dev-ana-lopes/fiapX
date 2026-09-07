from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.responses import Response
from fiapx_api.auth import _user_id, hash_refresh_token, make_token, new_refresh_token
from fiapx_api.config import Settings
from fiapx_api.main import REFRESH_COOKIE, _set_refresh_cookie


def test_access_token_contains_user_and_refresh_token_is_not_access_token() -> None:
    user_id = uuid4()

    access_token = make_token(user_id)
    assert _user_id(access_token) == user_id

    refresh_like_token = make_token(user_id, "refresh")
    with pytest.raises(HTTPException) as error:
        _user_id(refresh_like_token)
    assert error.value.status_code == 401


def test_refresh_token_is_opaque_and_hashed() -> None:
    token = new_refresh_token()

    assert len(token) > 40
    assert token != hash_refresh_token(token)
    assert len(hash_refresh_token(token)) == 64


def test_refresh_cookie_is_http_only_and_scoped_to_auth() -> None:
    response = Response()

    _set_refresh_cookie(response, "opaque-token")

    header = response.headers["set-cookie"].lower()
    assert f"{REFRESH_COOKIE}=opaque-token" in header
    assert "httponly" in header
    assert "samesite=lax" in header
    assert "path=/api/v1/auth" in header


def test_production_rejects_development_secrets() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET"):
        Settings(app_env="production")


def test_production_accepts_explicit_secrets() -> None:
    settings = Settings(
        app_env="production",
        jwt_secret="a" * 64,
        minio_secret_key="b" * 32,
    )

    assert settings.app_env == "production"
