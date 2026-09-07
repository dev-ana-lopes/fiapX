from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class VideoStatus(StrEnum):
    UPLOADING = "UPLOADING"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class VideoProcessingMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str = "video.uploaded"
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    job_id: UUID | None = None
    video_id: UUID
    user_id: UUID | None = None
    object_key: str
    attempt: int = 1
    correlation_id: str | None = None


class VideoEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    job_id: UUID | None = None
    video_id: UUID
    user_id: UUID | None = None
    status: VideoStatus
    error_message: str | None = None
    correlation_id: str | None = None
