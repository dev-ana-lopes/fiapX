import asyncio
import io
import logging
import mimetypes
import re
import tempfile
import zipfile
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fiapx_shared import VideoProcessingMessage, VideoStatus
from prometheus_client import Counter, make_asgi_app
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import (
    create_refresh_session,
    find_user,
    get_current_user,
    hash_refresh_token,
    make_token,
    password_hash,
    verify_password,
)
from .config import get_settings
from .db import engine, get_session, session_factory
from .messaging import declare_video_topology, publish_raw
from .minio_storage import MinioStorage
from .models import AuthSession, Notification, OutboxEvent, ProcessingJob, User, Video
from .progress import RedisProgressStore
from .schemas import (
    AuthRequest,
    AuthResponse,
    CurrentUserResponse,
    NotificationPage,
    NotificationResponse,
    RefreshRequest,
    VideoCreateResponse,
    VideoPage,
    VideoResponse,
)

logger = logging.getLogger(__name__)
settings = get_settings()
storage = MinioStorage()
videos_received = Counter("videos_received_total", "Videos accepted by the API")
REFRESH_COOKIE = "fiapx_refresh"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.app_env.lower() not in {"local", "test"},
        samesite="lax",
        path="/api/v1/auth",
    )


async def _auth_response(session: AsyncSession, user_id: UUID, response: Response) -> AuthResponse:
    refresh_token, _ = await create_refresh_session(session, user_id)
    await session.commit()
    _set_refresh_cookie(response, refresh_token)
    return AuthResponse(access_token=make_token(user_id), refresh_token=None)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    publisher_task = asyncio.create_task(outbox_publisher())
    yield
    publisher_task.cancel()
    await asyncio.gather(publisher_task, return_exceptions=True)
    await engine.dispose()


async def outbox_publisher() -> None:
    while True:
        try:
            from aio_pika import connect_robust

            connection = await connect_robust(settings.rabbitmq_url)
            async with connection:
                channel = await connection.channel(publisher_confirms=True)
                exchange, _ = await declare_video_topology(channel)
                while True:
                    published = await publish_pending_outbox(channel, exchange)
                    if not published:
                        await asyncio.sleep(settings.outbox_poll_interval_ms / 1000)

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("outbox.publisher.unavailable")
            await asyncio.sleep(settings.outbox_poll_interval_ms / 1000)


async def publish_pending_outbox(channel: object, exchange: object) -> int:
    """Claim and publish one batch; row locks prevent duplicate concurrent claims."""
    async with session_factory() as session:
        events = list(
            (
                await session.execute(
                    select(OutboxEvent)
                    .where(OutboxEvent.published_at.is_(None))
                    .order_by(OutboxEvent.created_at)
                    .with_for_update(skip_locked=True)
                    .limit(settings.outbox_batch_size)
                )
            ).scalars()
        )
        published_count = 0
        for event in events:
            try:
                await publish_raw(
                    channel,
                    exchange,
                    event.payload.encode(),
                    event.event_type,
                    str(event.id),
                )
                event.published_at = datetime.now(UTC)
                published_count += 1
            except Exception as exc:
                event.attempts += 1
                event.last_error = str(exc)[:500]
        await session.commit()
        return published_count


app = FastAPI(title="FIAP X API", version="0.2.0", lifespan=lifespan)


@app.middleware("http")
async def correlation_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[item.strip() for item in settings.cors_origins.split(",") if item.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
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
async def register(
    data: AuthRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    if await find_user(session, data.email):
        raise HTTPException(409, "email already registered")
    user = User(
        name=data.name or data.email.split("@", 1)[0],
        email=data.email,
        password_hash=password_hash(data.password),
    )
    session.add(user)
    await session.flush()
    return await _auth_response(session, user.id, response)


@api.post("/auth/login", response_model=AuthResponse, tags=["Auth"])
async def login(
    data: AuthRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    user = await find_user(session, data.email)
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "invalid credentials")
    return await _auth_response(session, user.id, response)


@api.post("/auth/refresh", response_model=AuthResponse, tags=["Auth"])
async def refresh(
    request: Request,
    response: Response,
    data: RefreshRequest | None = None,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    raw_token = request.cookies.get(REFRESH_COOKIE) or (data.refresh_token if data else None)
    if not raw_token:
        raise HTTPException(401, "invalid refresh token")
    auth_session = (
        await session.execute(
            select(AuthSession)
            .where(AuthSession.token_hash == hash_refresh_token(raw_token))
            .with_for_update()
        )
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if (
        auth_session is None
        or auth_session.revoked_at is not None
        or auth_session.expires_at <= now
    ):
        raise HTTPException(401, "invalid refresh token")
    user = await session.get(User, auth_session.user_id)
    if user is None:
        auth_session.revoked_at = now
        await session.commit()
        raise HTTPException(401, "invalid refresh token")
    auth_session.revoked_at = now
    auth_session.last_used_at = now
    new_token, _ = await create_refresh_session(session, user.id)
    await session.commit()
    _set_refresh_cookie(response, new_token)
    return AuthResponse(access_token=make_token(user.id), refresh_token=None)


@api.post("/auth/logout", status_code=204, tags=["Auth"])
async def logout(
    request: Request,
    response: Response,
    data: RefreshRequest | None = None,
    session: AsyncSession = Depends(get_session),
) -> None:
    raw_token = request.cookies.get(REFRESH_COOKIE) or (data.refresh_token if data else None)
    if raw_token:
        auth_session = (
            await session.execute(
                select(AuthSession).where(AuthSession.token_hash == hash_refresh_token(raw_token))
            )
        ).scalar_one_or_none()
        if auth_session and auth_session.revoked_at is None:
            auth_session.revoked_at = datetime.now(UTC)
            await session.commit()
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")


@api.get("/auth/me", response_model=CurrentUserResponse, tags=["Auth"])
async def current_user(user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(id=user.id, name=user.name, email=user.email)


@api.post(
    "/videos",
    response_model=VideoCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Videos"],
)
async def create_video(
    request: Request,
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
    message = VideoProcessingMessage(
        job_id=job_id,
        video_id=video_id,
        user_id=user.id,
        object_key=object_key,
        attempt=1,
        correlation_id=request.state.correlation_id,
    )
    session.add_all(
        [
            video,
            ProcessingJob(id=job_id, video_id=video_id, status=VideoStatus.QUEUED),
            OutboxEvent(
                event_type="video.uploaded",
                aggregate_id=video_id,
                payload=message.model_dump_json(),
            ),
        ]
    )
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        await storage.delete(object_key)
        raise
    videos_received.inc()
    return VideoCreateResponse(
        id=video_id,
        original_filename=filename,
        status=VideoStatus.QUEUED,
        created_at=video.created_at,
    )


def _response(
    video: Video, progress: int | None = None, progress_stage: str | None = None
) -> VideoResponse:
    return VideoResponse.model_validate(
        {
            **video.__dict__,
            "progress": progress if progress is not None else video.progress,
            "progress_stage": (
                progress_stage if progress_stage is not None else video.progress_stage
            ),
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
        raw_stage = await redis.client.get(f"video:{video.id}:stage")
        progress_stage = raw_stage.decode() if isinstance(raw_stage, bytes) else raw_stage
    finally:
        await redis.client.aclose()
    return _response(video, progress, progress_stage)


@api.get("/videos/{video_id}/thumbnail", tags=["Videos"])
async def video_thumbnail(
    video_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    video = (
        await session.execute(select(Video).where(Video.id == video_id, Video.user_id == user.id))
    ).scalar_one_or_none()
    if video is None or video.status != VideoStatus.COMPLETED or not video.result_object_key:
        raise HTTPException(404, "thumbnail not available")
    try:
        archive = await storage.read(video.result_object_key)
        with zipfile.ZipFile(io.BytesIO(archive)) as frames_zip:
            frame_names = sorted(
                name
                for name in frames_zip.namelist()
                if name.startswith("frame_") and name.lower().endswith(".jpg")
            )
            if not frame_names:
                raise ValueError("archive contains no frames")
            frame = frames_zip.read(frame_names[0])
    except (KeyError, ValueError, zipfile.BadZipFile) as exc:
        raise HTTPException(404, "thumbnail not available") from exc
    return Response(
        content=frame,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=3600"},
    )


@api.get("/videos/{video_id}/preview", tags=["Videos"])
async def video_preview(
    video_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    video = (
        await session.execute(select(Video).where(Video.id == video_id, Video.user_id == user.id))
    ).scalar_one_or_none()
    if video is None:
        raise HTTPException(404, "video not found")
    content = await storage.read(video.object_key)
    return Response(
        content=content,
        media_type=video.content_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )


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
    return {"url": f"/api/v1/videos/{video_id}/download/file"}


@api.get("/videos/{video_id}/download/file", tags=["Videos"])
async def download_video_file(
    video_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    video = (
        await session.execute(select(Video).where(Video.id == video_id, Video.user_id == user.id))
    ).scalar_one_or_none()
    if video is None or video.status != VideoStatus.COMPLETED or not video.result_object_key:
        raise HTTPException(404, "download not available")
    content = await storage.read(video.result_object_key)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="frames.zip"'},
    )


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


@api.get("/notifications", response_model=NotificationPage, tags=["Notifications"])
async def list_notifications(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> NotificationPage:
    result = await session.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(100)
    )
    unread_count = (
        await session.execute(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user.id, Notification.status == "PENDING")
        )
    ).scalar_one()
    return NotificationPage(
        items=[NotificationResponse.model_validate(item) for item in result.scalars()],
        unread_count=unread_count,
    )


@api.patch("/notifications/{notification_id}/read", status_code=204, tags=["Notifications"])
async def mark_notification_read(
    notification_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> None:
    notification = (
        await session.execute(
            select(Notification).where(
                Notification.id == notification_id, Notification.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if notification is None:
        raise HTTPException(404, "notification not found")
    notification.status = "READ"
    notification.read_at = datetime.now(UTC)
    await session.commit()


@api.post("/notifications/read-all", status_code=204, tags=["Notifications"])
async def mark_all_notifications_read(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> None:
    notifications = (
        await session.execute(
            select(Notification).where(
                Notification.user_id == user.id, Notification.status == "PENDING"
            )
        )
    ).scalars()
    now = datetime.now(UTC)
    for notification in notifications:
        notification.status = "READ"
        notification.read_at = now
    await session.commit()


app.include_router(api)
