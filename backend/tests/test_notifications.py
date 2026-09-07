from uuid import uuid4

from fiapx_notification_worker.main import notification_content
from fiapx_shared import VideoEvent, VideoStatus


def test_failed_event_content_includes_error() -> None:
    event = VideoEvent(
        event_type="video.processing.failed",
        video_id=uuid4(),
        user_id=uuid4(),
        status=VideoStatus.FAILED,
        error_message="arquivo corrompido",
    )

    assert notification_content(event, "sample.mp4") == (
        "VIDEO_FAILED",
        'Falha ao processar o vídeo "sample.mp4".',
        "arquivo corrompido",
    )


def test_completed_event_content_is_download_oriented() -> None:
    event = VideoEvent(
        event_type="video.processing.completed",
        video_id=uuid4(),
        user_id=uuid4(),
        status=VideoStatus.COMPLETED,
    )

    notification_type, title, message = notification_content(event, "sample.mp4")

    assert notification_type == "VIDEO_COMPLETED"
    assert '"sample.mp4"' in title
    assert "baixar" in message
