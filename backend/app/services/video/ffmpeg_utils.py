import os
import json
import shutil
import subprocess
from typing import Optional

TARGET_W = 1920
TARGET_H = 1080
TARGET_FPS = 30


def resolve_ffmpeg() -> Optional[str]:
    return os.environ.get("FFMPEG_BINARY") or shutil.which("ffmpeg")


def resolve_ffprobe() -> Optional[str]:
    return os.environ.get("FFPROBE_BINARY") or shutil.which("ffprobe")


def _require(bin_path: Optional[str], name: str) -> str:
    if not bin_path:
        raise RuntimeError(
            f"{name} not found. Install ffmpeg and ensure it is on PATH, or set the "
            f"{name.upper()}_BINARY environment variable."
        )
    return bin_path


def normalize_clip(src_path: str, dst_path: str,
                   width: int = TARGET_W, height: int = TARGET_H, fps: int = TARGET_FPS) -> str:
    """Transcode any clip to uniform H.264, fixed resolution (letterboxed), fps, NO audio."""
    ff = _require(resolve_ffmpeg(), "ffmpeg")
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,fps={fps}"
    )
    os.makedirs(os.path.dirname(dst_path) or ".", exist_ok=True)
    subprocess.run(
        [ff, "-y", "-i", src_path, "-vf", vf,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", dst_path],
        check=True, capture_output=True,
    )
    return dst_path


def probe_duration_ms(path: str) -> Optional[int]:
    fp = resolve_ffprobe()
    if not fp:
        return None
    try:
        out = subprocess.run(
            [fp, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        return round(float(out) * 1000)
    except (subprocess.CalledProcessError, ValueError):
        return None


def probe_stream_info(path: str) -> dict:
    """Return {width, height, fps, has_audio} via ffprobe JSON."""
    fp = _require(resolve_ffprobe(), "ffprobe")
    out = subprocess.run(
        [fp, "-v", "error", "-show_streams", "-of", "json", path],
        check=True, capture_output=True, text=True,
    ).stdout
    data = json.loads(out)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    fps = 0.0
    rate = video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1"
    try:
        num, den = rate.split("/")
        fps = float(num) / float(den) if float(den) else 0.0
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    return {
        "width": int(video.get("width", 0)),
        "height": int(video.get("height", 0)),
        "fps": fps,
        "has_audio": has_audio,
    }


def extract_last_frame(video_path: str, out_image_path: str) -> str:
    """Grab the final frame as a PNG (for tail-frame chaining)."""
    ff = _require(resolve_ffmpeg(), "ffmpeg")
    os.makedirs(os.path.dirname(out_image_path) or ".", exist_ok=True)
    subprocess.run(
        [ff, "-y", "-sseof", "-0.1", "-i", video_path,
         "-update", "1", "-frames:v", "1", out_image_path],
        check=True, capture_output=True,
    )
    return out_image_path


def trim_clip(src_path: str, dst_path: str, start_ms: int = 0,
              end_ms: Optional[int] = None) -> str:
    """Cut [start_ms, end_ms) out of a clip. Re-encodes so cuts land on exact
    frames rather than the nearest keyframe."""
    ff = _require(resolve_ffmpeg(), "ffmpeg")
    os.makedirs(os.path.dirname(dst_path) or ".", exist_ok=True)
    cmd = [ff, "-y", "-ss", f"{max(0, start_ms) / 1000:.3f}"]
    if end_ms is not None:
        cmd += ["-to", f"{max(0, end_ms) / 1000:.3f}"]
    cmd += ["-i", src_path, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", dst_path]
    subprocess.run(cmd, check=True, capture_output=True)
    return dst_path


def freeze_pad_clip(src_path: str, dst_path: str, pad_ms: int) -> str:
    """Extend a clip by holding its final frame for pad_ms.

    tpad is the whole trick: clone_mode=clone repeats the last frame rather than
    inserting black, which is the animatic convention for covering an overrun.
    """
    ff = _require(resolve_ffmpeg(), "ffmpeg")
    os.makedirs(os.path.dirname(dst_path) or ".", exist_ok=True)
    if pad_ms <= 0:
        subprocess.run(
            [ff, "-y", "-i", src_path, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", dst_path],
            check=True, capture_output=True,
        )
        return dst_path
    vf = f"tpad=stop_mode=clone:stop_duration={pad_ms / 1000:.3f}"
    subprocess.run(
        [ff, "-y", "-i", src_path, "-vf", vf,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", dst_path],
        check=True, capture_output=True,
    )
    return dst_path


def pad_audio(src_path: str, dst_path: str, total_ms: int) -> str:
    """Force audio to exactly total_ms — trailing silence if short, cut if long."""
    ff = _require(resolve_ffmpeg(), "ffmpeg")
    os.makedirs(os.path.dirname(dst_path) or ".", exist_ok=True)
    seconds = max(0, total_ms) / 1000
    subprocess.run(
        [ff, "-y", "-i", src_path,
         "-af", f"apad=whole_dur={seconds:.3f}",
         "-t", f"{seconds:.3f}", "-ar", "44100", "-ac", "2", dst_path],
        check=True, capture_output=True,
    )
    return dst_path


def silent_audio(dst_path: str, duration_ms: int) -> str:
    """A silent track, for a beat whose segment has no narration yet."""
    ff = _require(resolve_ffmpeg(), "ffmpeg")
    os.makedirs(os.path.dirname(dst_path) or ".", exist_ok=True)
    seconds = max(0, duration_ms) / 1000
    subprocess.run(
        [ff, "-y", "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
         "-t", f"{seconds:.3f}", dst_path],
        check=True, capture_output=True,
    )
    return dst_path
