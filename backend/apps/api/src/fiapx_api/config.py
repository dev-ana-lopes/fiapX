from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str = Field("postgresql+asyncpg://fiapx:fiapx@localhost:5432/fiapx")
    redis_url: str = "redis://localhost:6379/0"
    rabbitmq_url: str = "amqp://fiapx:fiapx@localhost:5672/"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "fiapx"
    minio_secret_key: str = "fiapxsecret"
    minio_bucket: str = "videos"
    minio_secure: bool = False
    max_upload_size_bytes: int = 524288000
    allowed_video_extensions: str = ".mp4,.mov,.avi,.mkv,.webm"
    video_frame_interval_seconds: float = 1.0
    download_url_expiration_seconds: int = 300
    video_processing_max_retries: int = 3
    app_name: str = "FIAP X API"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    cors_origins: str = "http://localhost:4200"


@lru_cache
def get_settings() -> Settings:
    return Settings()
