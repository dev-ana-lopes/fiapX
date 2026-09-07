from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from fiapx_shared import VideoStatus
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    videos: Mapped[list[Video]] = relationship(back_populates="user", cascade="all, delete-orphan")
    auth_sessions: Mapped[list[AuthSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user: Mapped[User] = relationship(back_populates="auth_sessions")


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        CheckConstraint("file_size >= 0", name="ck_videos_file_size_nonnegative"),
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_videos_progress_range"),
        CheckConstraint(
            "status IN ('UPLOADING', 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED')",
            name="ck_videos_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    object_key: Mapped[str] = mapped_column(String(500), unique=True)
    result_object_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[VideoStatus] = mapped_column(String(20), default=VideoStatus.UPLOADING)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    progress_stage: Mapped[str] = mapped_column(String(80), default="Aguardando processamento")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user: Mapped[User | None] = relationship(back_populates="videos")
    jobs: Mapped[list[ProcessingJob]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (
        CheckConstraint("attempt >= 0", name="ck_processing_jobs_attempt_nonnegative"),
        CheckConstraint(
            "status IN ('UPLOADING', 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED')",
            name="ck_processing_jobs_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    video_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("videos.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default=VideoStatus.QUEUED)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    video: Mapped[Video] = relationship(back_populates="jobs")


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(120))
    aggregate_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    event_id: Mapped[UUID | None] = mapped_column(Uuid, unique=True, index=True, nullable=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    video_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("videos.id"), index=True)
    type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user: Mapped[User] = relationship(back_populates="notifications")
    video: Mapped[Video] = relationship(back_populates="notifications")
