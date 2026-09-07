from unittest.mock import patch

from fiapx_video_worker.resilience import retry_delay, should_retry


def test_retry_delay_is_exponential_and_bounded() -> None:
    with patch("fiapx_video_worker.resilience.get_settings") as settings:
        settings.return_value.video_retry_base_delay_seconds = 5
        settings.return_value.video_retry_max_delay_seconds = 20
        settings.return_value.video_retry_jitter_seconds = 0
        assert retry_delay(1) == 5
        assert retry_delay(2) == 10
        assert retry_delay(4) == 20


def test_result_key_is_deterministic() -> None:
    user_id = "user-1"
    video_id = "video-1"
    assert (
        f"users/{user_id}/videos/{video_id}/result/frames.zip"
        == f"users/{user_id}/videos/{video_id}/result/frames.zip"
    )


def test_retry_policy_stops_at_configured_limit() -> None:
    assert should_retry(0, 3)
    assert should_retry(2, 3)
    assert not should_retry(3, 3)
    assert not should_retry(4, 3)
