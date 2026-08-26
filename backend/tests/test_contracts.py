from uuid import uuid4

from fiapx_shared import VideoProcessingMessage, VideoStatus


def test_processing_message_is_strongly_typed() -> None:
    message = VideoProcessingMessage(job_id=uuid4(), video_id=uuid4(), object_key="uploads/a.mp4")
    assert message.object_key == "uploads/a.mp4"
    assert VideoStatus.QUEUED.value == "QUEUED"
