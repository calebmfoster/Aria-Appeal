import os
import subprocess
import pytest
from app.services.video import ffmpeg_utils


def _ffmpeg_available():
    try:
        return ffmpeg_utils.resolve_ffmpeg() is not None and ffmpeg_utils.resolve_ffprobe() is not None
    except Exception:
        return False


requires_ffmpeg = pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg/ffprobe not resolvable in this shell")


def test_resolvers_return_string_or_none():
    assert ffmpeg_utils.resolve_ffmpeg() is None or isinstance(ffmpeg_utils.resolve_ffmpeg(), str)
    assert ffmpeg_utils.resolve_ffprobe() is None or isinstance(ffmpeg_utils.resolve_ffprobe(), str)


@requires_ffmpeg
def test_normalize_and_probe(tmp_path):
    ff = ffmpeg_utils.resolve_ffmpeg()
    src = str(tmp_path / "src.mp4")
    subprocess.run(
        [ff, "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=15:duration=2",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
         "-shortest", "-pix_fmt", "yuv420p", src],
        check=True, capture_output=True,
    )
    dst = str(tmp_path / "out.mp4")
    out = ffmpeg_utils.normalize_clip(src, dst)
    assert out == dst and os.path.exists(dst)

    info = ffmpeg_utils.probe_stream_info(dst)
    assert info["width"] == 1920 and info["height"] == 1080
    assert abs(info["fps"] - 30.0) < 0.5
    assert info["has_audio"] is False

    dur = ffmpeg_utils.probe_duration_ms(dst)
    assert 1500 <= dur <= 2500


@requires_ffmpeg
def test_extract_last_frame(tmp_path):
    ff = ffmpeg_utils.resolve_ffmpeg()
    src = str(tmp_path / "src.mp4")
    subprocess.run(
        [ff, "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=15:duration=2",
         "-pix_fmt", "yuv420p", src],
        check=True, capture_output=True,
    )
    out_png = str(tmp_path / "last.png")
    res = ffmpeg_utils.extract_last_frame(src, out_png)
    assert res == out_png and os.path.exists(out_png) and os.path.getsize(out_png) > 0
