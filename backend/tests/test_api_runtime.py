import asyncio
import os
from uuid import uuid4

import httpx
import pytest

RUNTIME_URL = os.getenv("FIAPX_RUNTIME_URL")
VIDEO_PATH = os.getenv("FIAPX_TEST_VIDEO")
INVALID_VIDEO_PATH = os.getenv("FIAPX_INVALID_VIDEO")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not RUNTIME_URL, reason="FIAPX_RUNTIME_URL is not configured"),
]


async def register(client: httpx.AsyncClient, suffix: str) -> tuple[str, str]:
    email = f"runtime-{suffix}-{uuid4().hex[:8]}@example.com"
    response = await client.post(
        "/auth/register", json={"name": suffix, "email": email, "password": "DemoPass123!"}
    )
    assert response.status_code == 201, response.text
    assert response.headers.get("x-correlation-id")
    return email, response.json()["access_token"]


@pytest.mark.asyncio
async def test_auth_refresh_rotation_logout_and_ownership() -> None:
    assert RUNTIME_URL is not None
    async with httpx.AsyncClient(base_url=RUNTIME_URL) as client:
        _, user_a_token = await register(client, "owner")
        _, user_b_token = await register(client, "other")
        token_a_headers = {"Authorization": f"Bearer {user_a_token}"}
        token_b_headers = {"Authorization": f"Bearer {user_b_token}"}

        refresh_cookie = client.cookies.get("fiapx_refresh")
        assert refresh_cookie
        rotated = await client.post("/auth/refresh", json={})
        assert rotated.status_code == 200, rotated.text
        assert rotated.json()["refresh_token"] is None
        assert client.cookies.get("fiapx_refresh") != refresh_cookie

        old_client = httpx.AsyncClient(base_url=RUNTIME_URL)
        try:
            old_refresh = await old_client.post(
                "/auth/refresh", json={"refresh_token": refresh_cookie}
            )
        finally:
            await old_client.aclose()
        assert old_refresh.status_code == 401

        logout = await client.post("/auth/logout", json={})
        assert logout.status_code == 204
        assert (await client.post("/auth/refresh", json={})).status_code == 401

        if VIDEO_PATH:
            with open(VIDEO_PATH, "rb") as video_file:
                upload = await client.post(
                    "/videos",
                    headers=token_a_headers,
                    files={"file": ("runtime.mp4", video_file, "video/mp4")},
                )
            assert upload.status_code == 202, upload.text
            video_id = upload.json()["id"]
            final = None
            observed_stages: set[str] = set()
            for _ in range(150):
                await asyncio.sleep(0.2)
                final = await client.get(f"/videos/{video_id}", headers=token_a_headers)
                if final.status_code == 200:
                    payload = final.json()
                    observed_stages.add(payload["progress_stage"])
                    assert 0 <= payload["progress"] <= 100
                if final.json()["status"] in {"COMPLETED", "FAILED"}:
                    break
            assert final is not None and final.status_code == 200
            assert final.json()["progress_stage"] in {"Concluído", "Falha no processamento"}
            assert observed_stages
            assert (
                await client.get(f"/videos/{video_id}", headers=token_b_headers)
            ).status_code == 404
            assert (await client.get("/videos", headers=token_b_headers)).json()["total"] == 0

        if INVALID_VIDEO_PATH:
            with open(INVALID_VIDEO_PATH, "rb") as invalid_file:
                upload = await client.post(
                    "/videos",
                    headers=token_a_headers,
                    files={"file": ("invalid.mp4", invalid_file, "video/mp4")},
                )
            assert upload.status_code == 202, upload.text
            invalid_id = upload.json()["id"]
            invalid_final = None
            for _ in range(150):
                await asyncio.sleep(0.2)
                invalid_final = await client.get(f"/videos/{invalid_id}", headers=token_a_headers)
                if invalid_final.json()["status"] in {"COMPLETED", "FAILED"}:
                    break
            assert invalid_final is not None and invalid_final.status_code == 200
            assert invalid_final.json()["status"] == "FAILED"
            notifications = await client.get("/notifications", headers=token_a_headers)
            assert notifications.status_code == 200
            assert any(
                item["video_id"] == invalid_id and item["type"] == "VIDEO_FAILED"
                for item in notifications.json()["items"]
            )
