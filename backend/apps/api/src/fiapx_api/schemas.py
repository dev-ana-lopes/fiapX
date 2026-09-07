from datetime import datetime
from uuid import UUID

from fiapx_shared import VideoStatus
from pydantic import BaseModel, ConfigDict


class VideoCreateResponse(BaseModel):
    id: UUID
    original_filename: str
    status: VideoStatus
    progress: int = 0
    created_at: datetime


class AuthRequest(BaseModel):
    email: str
    password: str
    name: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    # Body support is retained for non-browser API clients; browsers use the HttpOnly cookie.
    refresh_token: str | None = None


class CurrentUserResponse(BaseModel):
    id: UUID
    name: str
    email: str


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    original_filename: str
    status: VideoStatus
    progress: int
    progress_stage: str
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    download_available: bool = False


class VideoPage(BaseModel):
    items: list[VideoResponse]
    page: int
    page_size: int
    total: int


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    video_id: UUID
    type: str
    status: str
    title: str | None
    message: str | None
    created_at: datetime
    read_at: datetime | None


class NotificationPage(BaseModel):
    items: list[NotificationResponse]
    unread_count: int
