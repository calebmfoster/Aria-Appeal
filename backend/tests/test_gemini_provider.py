import asyncio
import os
import types as pytypes

import pytest
from google.genai import types as gtypes

from app.services.video.base import VideoGenRequest
from app.services.video.gemini_provider import GeminiVeoProvider


class _FakeOp:
    def __init__(self, finish_after: int = 1):
        self.done = False
        self.error = None
        self.polls = 0
        self._finish_after = finish_after
        self.response = pytypes.SimpleNamespace(
            generated_videos=[pytypes.SimpleNamespace(video=gtypes.Video(uri="files/fake"))]
        )


class _FakeModels:
    def __init__(self, op):
        self._op = op
        self.last_kwargs = None

    def generate_videos(self, **kwargs):
        self.last_kwargs = kwargs
        return self._op


class _FakeOperations:
    def get(self, op):
        op.polls += 1
        if op.polls >= op._finish_after:
            op.done = True
        return op


class _FakeFiles:
    def download(self, *, file):
        return b"FAKE_MP4_BYTES"


class _FakeClient:
    def __init__(self, op):
        self.models = _FakeModels(op)
        self.operations = _FakeOperations()
        self.files = _FakeFiles()


def _provider(tmp_path, **kw):
    kw.setdefault("api_key", "test-key")
    kw.setdefault("model", "veo-3.0-generate-001")
    kw.setdefault("out_dir", str(tmp_path))
    kw.setdefault("poll_interval_s", 0)
    kw.setdefault("timeout_s", 10)
    return GeminiVeoProvider(**kw)


def _run(provider, req, client):
    provider._make_client = lambda: client
    return asyncio.run(provider.generate(req))


def test_generate_writes_file_and_composes_prompt(tmp_path):
    client = _FakeClient(_FakeOp())
    p = _provider(tmp_path)
    req = VideoGenRequest(
        prompt="a volunteer", style_prompt="golden hour", character_sheet="MARIA: 60s"
    )
    res = _run(p, req, client)

    assert os.path.exists(res.video_path)
    with open(res.video_path, "rb") as f:
        assert f.read() == b"FAKE_MP4_BYTES"

    sent = client.models.last_kwargs["prompt"]
    assert "a volunteer" in sent and "golden hour" in sent and "MARIA" in sent
    assert client.models.last_kwargs["model"] == "veo-3.0-generate-001"


def test_config_strips_audio_and_sets_render_targets(tmp_path):
    """We normalize to silent 1920x1080 downstream, so Veo must not bill us for a
    soundtrack we discard, and should render at the resolution we actually keep."""
    client = _FakeClient(_FakeOp())
    p = _provider(tmp_path)
    _run(p, VideoGenRequest(prompt="x", negative_prompt="text overlays"), client)

    cfg = client.models.last_kwargs["config"]
    assert cfg.generate_audio is False
    assert cfg.resolution == "1080p"
    assert cfg.aspect_ratio == "16:9"
    assert cfg.person_generation == "allow_adult"
    assert cfg.negative_prompt == "text overlays"
    assert cfg.number_of_videos == 1


def test_init_image_is_passed_as_first_frame(tmp_path):
    img = tmp_path / "tail.png"
    img.write_bytes(b"\x89PNG fake")
    client = _FakeClient(_FakeOp())
    p = _provider(tmp_path)
    _run(p, VideoGenRequest(prompt="x", init_image_path=str(img)), client)

    image = client.models.last_kwargs["image"]
    assert image is not None
    assert image.mime_type == "image/png"
    assert image.image_bytes == b"\x89PNG fake"


def test_reference_images_are_tagged_as_asset(tmp_path):
    ref = tmp_path / "maria.jpg"
    ref.write_bytes(b"jpegbytes")
    client = _FakeClient(_FakeOp())
    p = _provider(tmp_path)
    _run(p, VideoGenRequest(prompt="x", reference_image_paths=[str(ref)]), client)

    refs = client.models.last_kwargs["config"].reference_images
    assert len(refs) == 1
    assert refs[0].reference_type == gtypes.VideoGenerationReferenceType.ASSET
    assert refs[0].image.mime_type == "image/jpeg"


def test_missing_reference_image_is_skipped(tmp_path):
    client = _FakeClient(_FakeOp())
    p = _provider(tmp_path)
    _run(p, VideoGenRequest(prompt="x", reference_image_paths=["/no/such/file.png"]), client)
    assert not client.models.last_kwargs["config"].reference_images


def test_polls_until_done(tmp_path):
    op = _FakeOp(finish_after=3)
    client = _FakeClient(op)
    p = _provider(tmp_path)
    _run(p, VideoGenRequest(prompt="x"), client)
    assert op.polls == 3


def test_operation_error_raises(tmp_path):
    op = _FakeOp()
    op.error = {"message": "quota exceeded"}
    op.done = True
    client = _FakeClient(op)
    p = _provider(tmp_path)
    with pytest.raises(RuntimeError, match="quota exceeded"):
        _run(p, VideoGenRequest(prompt="x"), client)


def test_timeout_raises_even_with_zero_poll_interval(tmp_path):
    """A zero poll interval must not defeat the deadline (it would if the loop
    tracked elapsed time by summing the sleep duration)."""
    op = _FakeOp(finish_after=10**9)  # never finishes
    client = _FakeClient(op)
    p = _provider(tmp_path, poll_interval_s=0, timeout_s=0)
    with pytest.raises(TimeoutError):
        _run(p, VideoGenRequest(prompt="x"), client)


def test_missing_api_key_raises(tmp_path):
    client = _FakeClient(_FakeOp())
    p = _provider(tmp_path, api_key="")
    with pytest.raises(RuntimeError, match="Gemini API key"):
        _run(p, VideoGenRequest(prompt="x"), client)
