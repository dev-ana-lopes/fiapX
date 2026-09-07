from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://fiapx:fiapx@localhost:5432/fiapx"
    redis_url: str = "redis://localhost:6379/0"
    rabbitmq_url: str = "amqp://fiapx:fiapx@localhost:5672/"
    minio_endpoint: str = "localhost:9000"
    minio_public_endpoint: str | None = None
    minio_access_key: str = "fiapx"
    minio_secret_key: str = "fiapxsecret"
    minio_bucket: str = "videos"
    minio_secure: bool = False
    max_upload_size_bytes: int = 524288000
    allowed_video_extensions: str = ".mp4,.mov,.avi,.mkv,.webm"
    video_frame_interval_seconds: float = 1.0
    video_max_duration_seconds: int = 3600
    video_max_width: int = 3840
    video_max_height: int = 2160
    download_url_expiration_seconds: int = 300
    video_processing_max_retries: int = 3
    video_retry_base_delay_seconds: int = 5
    video_retry_max_delay_seconds: int = 300
    video_retry_jitter_seconds: int = 2
    video_worker_prefetch: int = 1
    video_processing_lease_seconds: int = 120
    video_processing_lease_renew_seconds: int = 30
    outbox_poll_interval_ms: int = 1000
    outbox_batch_size: int = 20
    ffmpeg_timeout_seconds: int = 3600
    ffprobe_timeout_seconds: int = 30
    app_name: str = "FIAP X API"
    jwt_secret: str = "local-development-only-not-for-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    cors_origins: str = "http://localhost:4200"

    @model_validator(mode="after")
    def reject_insecure_production_defaults(self) -> Settings:
        if self.app_env.lower() not in {"local", "test"}:
            if self.jwt_secret == "local-development-only-not-for-production":
                raise ValueError("JWT_SECRET must be explicitly configured outside local/test")
            if self.minio_secret_key == "fiapxsecret":
                raise ValueError(
                    "MINIO_SECRET_KEY must be explicitly configured outside local/test"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
