import os
import subprocess

import pytest

from app.services.video import ffmpeg_utils
from app.services.video.assembly import Beat, assemble


def _available():
    try:
        return bool(ffmpeg_utils.resolve_ffmpeg()) and bool(ffmpeg_utils.resolve_ffprobe())
    except Exception:
        return False


requires_ffmpeg = pytest.mark.skipif(not _available(), reason="ffmpeg/ffprobe not resolvable")


def _clip(path, seconds, pattern="testsrc"):
    ff = ffmpeg_utils.resolve_ffmpeg()
    subprocess.run(
        [ff, "-y", "-f", "lavfi", "-i", f"{pattern}=size=320x240:rate=25:duration={seconds}",
         "-pix_fmt", "yuv420p", path],
        check=True, capture_output=True,
    )
    return path


def _wav(path, seconds):
    ff = ffmpeg_utils.resolve_ffmpeg()
    subprocess.run(
        [ff, "-y", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", path],
        check=True, capture_output=True,
    )
    return path


@requires_ffmpeg
def test_assembles_two_beats(tmp_path):
    c1 = _clip(str(tmp_path / "c1.mp4"), 3)
    c2 = _clip(str(tmp_path / "c2.mp4"), 2, pattern="smptebars")
    a1 = _wav(str(tmp_path / "a1.wav"), 2)
    a2 = _wav(str(tmp_path / "a2.wav"), 2)

    beats = [
        Beat(c1, a1, "first line", 0, 3000, 2000, 0, 0, None),
        Beat(c2, a2, "second line", 3000, 2000, 2000, 0, 0, None),
    ]
    out = str(tmp_path / "out.mp4")
    assemble(beats, out, {"enabled": True}, work_dir=str(tmp_path / "work"))

    assert os.path.exists(out)
    dur = ffmpeg_utils.probe_duration_ms(out)
    assert 4600 <= dur <= 5400, f"expected ~5s, got {dur}ms"

    info = ffmpeg_utils.probe_stream_info(out)
    assert info["width"] == ffmpeg_utils.TARGET_W
    assert info["height"] == ffmpeg_utils.TARGET_H
    assert abs(info["fps"] - ffmpeg_utils.TARGET_FPS) < 1.0
    assert info["has_audio"] is True


@requires_ffmpeg
def test_freeze_pads_when_narration_outruns_clip(tmp_path):
    c1 = _clip(str(tmp_path / "c1.mp4"), 2)
    a1 = _wav(str(tmp_path / "a1.wav"), 4)

    beats = [Beat(c1, a1, "long line", 0, 4000, 4000, 2000, 0, None)]
    out = str(tmp_path / "out.mp4")
    assemble(beats, out, {"enabled": True}, work_dir=str(tmp_path / "work"))

    dur = ffmpeg_utils.probe_duration_ms(out)
    assert 3700 <= dur <= 4400, f"expected ~4s, got {dur}ms"


@requires_ffmpeg
def test_beat_without_audio_gets_silence(tmp_path):
    c1 = _clip(str(tmp_path / "c1.mp4"), 2)
    beats = [Beat(c1, None, "unspoken", 0, 2000, 0, 0, 0, None)]
    out = str(tmp_path / "out.mp4")
    assemble(beats, out, {"enabled": True}, work_dir=str(tmp_path / "work"))

    assert os.path.exists(out)
    info = ffmpeg_utils.probe_stream_info(out)
    assert info["has_audio"] is True


@requires_ffmpeg
def test_subtitles_disabled_still_assembles(tmp_path):
    c1 = _clip(str(tmp_path / "c1.mp4"), 2)
    a1 = _wav(str(tmp_path / "a1.wav"), 2)
    beats = [Beat(c1, a1, "hidden", 0, 2000, 2000, 0, 0, None)]
    out = str(tmp_path / "out.mp4")
    assemble(beats, out, {"enabled": False}, work_dir=str(tmp_path / "work"))
    assert os.path.exists(out)


@requires_ffmpeg
def test_empty_beats_raises(tmp_path):
    with pytest.raises(ValueError):
        assemble([], str(tmp_path / "out.mp4"), {}, work_dir=str(tmp_path / "work"))
