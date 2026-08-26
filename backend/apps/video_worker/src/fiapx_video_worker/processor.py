import asyncio
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
    async def extract_frames(self, input_path: Path, output_dir: Path) -> ProcessingResult:
        output_dir.mkdir(parents=True, exist_ok=True)
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
            raise RuntimeError("ffmpeg processing timed out") from exc
        if process.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {stderr.decode(errors='replace')[-500:]}")
        frames = sorted(output_dir.glob("frame_*.jpg"))
        if not frames:
            raise RuntimeError("ffmpeg produced no frames")
        return ProcessingResult(len(frames), None, output_dir)


def make_zip(frames_dir: Path, destination: Path) -> Path:
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for frame in sorted(frames_dir.glob("frame_*.jpg")):
            archive.write(frame, frame.name)
    return destination
