import logging
import mimetypes
import re
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID, uuid4

import jwt
from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fiapx_shared import VideoProcessingMessage, VideoStatus
from prometheus_client import Counter, make_asgi_app
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import (
    find_user,
    get_current_user,
    make_token,
    password_hash,
    verify_password,
)
from .config import get_settings
from .db import engine, get_session
from .messaging import RabbitPublisher
from .minio_storage import MinioStorage
from .models import ProcessingJob, User, Video
from .progress import RedisProgressStore
from .schemas import (
    AuthRequest,
    AuthResponse,
    VideoCreateResponse,
    VideoPage,
    VideoResponse,
)

logger = logging.getLogger(__name__)
settings = get_settings()
storage = MinioStorage()
videos_received = Counter("videos_received_total", "Videos accepted by the API")


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="FIAP X API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[item.strip() for item in settings.cors_origins.split(",") if item.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/metrics", make_asgi_app())
api = APIRouter(prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
        await storage.exists("__readiness_probe__")
    except Exception as exc:
        raise HTTPException(503, "dependencies unavailable") from exc
    return {"status": "ready"}


@api.post("/auth/register", response_model=AuthResponse, status_code=201, tags=["Auth"])
async def register(data: AuthRequest, session: AsyncSession = Depends(get_session)) -> AuthResponse:
    if await find_user(session, data.email):
        raise HTTPException(409, "email already registered")
    user = User(
        name=data.name or data.email.split("@", 1)[0],
        email=data.email,
        password_hash=password_hash(data.password),
    )
    session.add(user)
    await session.commit()
    return AuthResponse(
        access_token=make_token(user.id), refresh_token=make_token(user.id, "refresh")
    )


@api.post("/auth/login", response_model=AuthResponse, tags=["Auth"])
async def login(data: AuthRequest, session: AsyncSession = Depends(get_session)) -> AuthResponse:
    user = await find_user(session, data.email)
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "invalid credentials")
    return AuthResponse(
        access_token=make_token(user.id), refresh_token=make_token(user.id, "refresh")
    )


@api.post("/auth/refresh", response_model=AuthResponse, tags=["Auth"])
async def refresh(data: dict[str, str]) -> AuthResponse:
    try:
        payload = jwt.decode(
            data["refresh_token"], settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "refresh":
            raise ValueError
        user_id = UUID(str(payload["sub"]))
    except (KeyError, ValueError, jwt.PyJWTError) as exc:
        raise HTTPException(401, "invalid refresh token") from exc
    return AuthResponse(
        access_token=make_token(user_id), refresh_token=make_token(user_id, "refresh")
    )


@api.post("/auth/logout", status_code=204, tags=["Auth"])
async def logout() -> None:
    return None


@api.post(
    "/videos",
    response_model=VideoCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Videos"],
)
async def create_video(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> VideoCreateResponse:
    filename = Path(re.split(r"[/\\]", file.filename or "")[-1]).name
    filename = re.sub(r"[\x00-\x1f\x7f]", "_", filename)[:255]
    extension = Path(filename).suffix.lower()
    allowed = {item.strip().lower() for item in settings.allowed_video_extensions.split(",")}
    if not filename or extension not in allowed:
        raise HTTPException(400, "unsupported video format")
    if file.content_type and not (
        file.content_type.startswith("video/")
        or file.content_type in {"application/octet-stream", "binary/octet-stream"}
    ):
        raise HTTPException(400, "invalid video content type")
    video_id, job_id = uuid4(), uuid4()
    object_key = f"users/{user.id}/videos/{video_id}/original/{video_id}{extension}"
    with tempfile.NamedTemporaryFile(prefix="fiapx-upload-", suffix=extension, delete=True) as temp:
        size = 0
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_size_bytes:
                raise HTTPException(413, "file too large")
            temp.write(chunk)
        temp.flush()
        if size == 0:
            raise HTTPException(400, "video file is empty")
        await storage.upload(
            object_key, Path(temp.name), file.content_type or mimetypes.guess_type(filename)[0]
        )
    video = Video(
        id=video_id,
        user_id=user.id,
        original_filename=filename,
        content_type=file.content_type or "application/octet-stream",
        file_size=size,
        object_key=object_key,
        status=VideoStatus.QUEUED,
    )
    session.add_all([video, ProcessingJob(id=job_id, video_id=video_id, status=VideoStatus.QUEUED)])
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        await storage.delete(object_key)
        raise
    try:
        await RabbitPublisher().publish(
            VideoProcessingMessage(
                job_id=job_id, video_id=video_id, user_id=user.id, object_key=object_key, attempt=1
            )
        )
    except Exception as exc:
        video.status, video.error_message = (
            VideoStatus.FAILED,
            "não foi possível enfileirar o vídeo",
        )
        await session.commit()
        logger.exception("video_event_publish_failed", extra={"video_id": str(video_id)})
        raise HTTPException(503, "processing queue unavailable") from exc
    videos_received.inc()
    return VideoCreateResponse(
        id=video_id,
        original_filename=filename,
        status=VideoStatus.QUEUED,
        created_at=video.created_at,
    )


def _response(video: Video, progress: int | None = None) -> VideoResponse:
    return VideoResponse.model_validate(
        {
            **video.__dict__,
            "progress": progress if progress is not None else video.progress,
            "download_available": video.status == VideoStatus.COMPLETED
            and bool(video.result_object_key),
        }
    )


@api.get("/videos", response_model=VideoPage, tags=["Videos"])
async def list_videos(
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> VideoPage:
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    total = (
        await session.execute(
            select(func.count()).select_from(Video).where(Video.user_id == user.id)
        )
    ).scalar_one()
    result = await session.execute(
        select(Video)
        .where(Video.user_id == user.id)
        .order_by(Video.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return VideoPage(
        items=[_response(video) for video in result.scalars()],
        page=page,
        page_size=page_size,
        total=total,
    )


@api.get("/videos/{video_id}", response_model=VideoResponse, tags=["Videos"])
async def get_video(
    video_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> VideoResponse:
    video = (
        await session.execute(select(Video).where(Video.id == video_id, Video.user_id == user.id))
    ).scalar_one_or_none()
    if video is None:
        raise HTTPException(404, "video not found")
    redis = RedisProgressStore()
    try:
        value = await redis.client.get(f"video:{video.id}:progress")
        progress = int(value) if value is not None else None
    finally:
        await redis.client.aclose()
    return _response(video, progress)


@api.get("/videos/{video_id}/download", tags=["Videos"])
async def download_video(
    video_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    video = (
        await session.execute(select(Video).where(Video.id == video_id, Video.user_id == user.id))
    ).scalar_one_or_none()
    if video is None or video.status != VideoStatus.COMPLETED or not video.result_object_key:
        raise HTTPException(404, "download not available")
    return {
        "url": await storage.presigned_get(
            video.result_object_key, settings.download_url_expiration_seconds
        )
    }


@api.delete("/videos/{video_id}", status_code=204, tags=["Videos"])
async def delete_video(
    video_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> None:
    video = (
        await session.execute(select(Video).where(Video.id == video_id, Video.user_id == user.id))
    ).scalar_one_or_none()
    if video is None:
        raise HTTPException(404, "video not found")
    await storage.delete(video.object_key)
    if video.result_object_key:
        await storage.delete(video.result_object_key)
    await session.delete(video)
    await session.commit()


app.include_router(api)
