import os
import subprocess

import pytest

from app.services.video import ffmpeg_utils


def _available():
    try:
        return bool(ffmpeg_utils.resolve_ffmpeg()) and bool(ffmpeg_utils.resolve_ffprobe())
    except Exception:
        return False


requires_ffmpeg = pytest.mark.skipif(not _available(), reason="ffmpeg/ffprobe not resolvable")


def _make_clip(path, seconds=4, rate=30):
    ff = ffmpeg_utils.resolve_ffmpeg()
    subprocess.run(
        [ff, "-y", "-f", "lavfi", "-i", f"testsrc=size=320x240:rate={rate}:duration={seconds}",
         "-pix_fmt", "yuv420p", path],
        check=True, capture_output=True,
    )
    return path


def _make_wav(path, seconds=2):
    ff = ffmpeg_utils.resolve_ffmpeg()
    subprocess.run(
        [ff, "-y", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", path],
        check=True, capture_output=True,
    )
    return path


@requires_ffmpeg
def test_trim_clip_cuts_to_range(tmp_path):
    src = _make_clip(str(tmp_path / "src.mp4"), seconds=6)
    dst = str(tmp_path / "trim.mp4")
    ffmpeg_utils.trim_clip(src, dst, 1000, 4000)
    dur = ffmpeg_utils.probe_duration_ms(dst)
    assert 2800 <= dur <= 3200


@requires_ffmpeg
def test_trim_clip_open_ended(tmp_path):
    src = _make_clip(str(tmp_path / "src.mp4"), seconds=5)
    dst = str(tmp_path / "trim.mp4")
    ffmpeg_utils.trim_clip(src, dst, 2000, None)
    dur = ffmpeg_utils.probe_duration_ms(dst)
    assert 2800 <= dur <= 3200


@requires_ffmpeg
def test_freeze_pad_extends_not_truncates(tmp_path):
    src = _make_clip(str(tmp_path / "src.mp4"), seconds=3)
    dst = str(tmp_path / "padded.mp4")
    ffmpeg_utils.freeze_pad_clip(src, dst, 2000)
    dur = ffmpeg_utils.probe_duration_ms(dst)
    assert 4700 <= dur <= 5300, f"expected ~5s, got {dur}ms"


@requires_ffmpeg
def test_freeze_pad_zero_is_a_passthrough(tmp_path):
    src = _make_clip(str(tmp_path / "src.mp4"), seconds=3)
    dst = str(tmp_path / "same.mp4")
    ffmpeg_utils.freeze_pad_clip(src, dst, 0)
    assert os.path.exists(dst)
    dur = ffmpeg_utils.probe_duration_ms(dst)
    assert 2800 <= dur <= 3200


@requires_ffmpeg
def test_pad_audio_adds_trailing_silence(tmp_path):
    src = _make_wav(str(tmp_path / "a.wav"), seconds=2)
    dst = str(tmp_path / "padded.wav")
    ffmpeg_utils.pad_audio(src, dst, 5000)
    dur = ffmpeg_utils.probe_duration_ms(dst)
    assert 4800 <= dur <= 5200


@requires_ffmpeg
def test_pad_audio_shorter_target_truncates(tmp_path):
    src = _make_wav(str(tmp_path / "a.wav"), seconds=4)
    dst = str(tmp_path / "cut.wav")
    ffmpeg_utils.pad_audio(src, dst, 2000)
    dur = ffmpeg_utils.probe_duration_ms(dst)
    assert 1800 <= dur <= 2200


@requires_ffmpeg
def test_silent_audio_has_expected_duration(tmp_path):
    dst = str(tmp_path / "silence.wav")
    ffmpeg_utils.silent_audio(dst, 3000)
    dur = ffmpeg_utils.probe_duration_ms(dst)
    assert 2800 <= dur <= 3200
