import asyncio
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from fiapx_api.config import get_settings


@dataclass(frozen=True)
class ProcessingResult:
    frame_count: int
    duration_seconds: float | None
    output_directory: Path


class VideoProcessor:
    async def extract_frames(
        self, input_path: Path, output_dir: Path, duration: float | None = None
    ) -> ProcessingResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        if duration is None:
            duration = await self.probe(input_path)
        fps = 1 / get_settings().video_frame_interval_seconds
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(input_path),
            "-vf",
            f"fps={fps:g}",
            str(output_dir / "frame_%06d.jpg"),
        ]
        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            _, stderr = await asyncio.wait_for(
                process.communicate(), timeout=get_settings().ffmpeg_timeout_seconds
            )
        except TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise TimeoutError("ffmpeg processing timed out") from exc
        if process.returncode != 0:
            raise ValueError(f"ffmpeg failed: {stderr.decode(errors='replace')[-500:]}")
        frames = sorted(output_dir.glob("frame_*.jpg"))
        if not frames:
            raise ValueError("ffmpeg produced no frames")
        return ProcessingResult(len(frames), duration, output_dir)

    async def probe(self, input_path: Path) -> float | None:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,width,height",
            "-of",
            "json",
            str(input_path),
        ]
        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=get_settings().ffprobe_timeout_seconds
            )
        except TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise ValueError("ffprobe validation timed out") from exc
        if process.returncode != 0:
            raise ValueError(f"video probe failed: {stderr.decode(errors='replace')[-500:]}")
        try:
            metadata = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise ValueError("video probe returned invalid metadata") from exc
        streams = [
            stream for stream in metadata.get("streams", []) if stream.get("codec_type") == "video"
        ]
        if not streams:
            raise ValueError("file does not contain a video stream")
        settings = get_settings()
        for stream in streams:
            if (
                int(stream.get("width") or 0) > settings.video_max_width
                or int(stream.get("height") or 0) > settings.video_max_height
            ):
                raise ValueError("video resolution exceeds configured limit")
        raw_duration = metadata.get("format", {}).get("duration")
        duration = float(raw_duration) if raw_duration is not None else None
        if duration is not None and duration > settings.video_max_duration_seconds:
            raise ValueError("video duration exceeds configured limit")
        return duration


def make_zip(frames_dir: Path, destination: Path) -> Path:
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for frame in sorted(frames_dir.glob("frame_*.jpg")):
            archive.write(frame, frame.name)
    return destination
