from zipfile import ZipFile

from fiapx_video_worker.processor import make_zip


def test_make_zip_contains_only_extracted_frames(tmp_path) -> None:
    frames = tmp_path / "frames"
    frames.mkdir()
    (frames / "frame_000002.jpg").write_bytes(b"second")
    (frames / "frame_000001.jpg").write_bytes(b"first")
    (frames / "ignored.txt").write_text("not a frame")

    archive = make_zip(frames, tmp_path / "frames.zip")

    with ZipFile(archive) as zipped:
        assert zipped.namelist() == ["frame_000001.jpg", "frame_000002.jpg"]
        assert zipped.read("frame_000001.jpg") == b"first"
