from datetime import datetime
from uuid import UUID

from fiapx_shared.contracts import VideoStatus
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


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    original_filename: str
    status: VideoStatus
    progress: int
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
