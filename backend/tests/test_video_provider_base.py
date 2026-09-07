import inspect
import pytest
from app.services.video.base import VideoGenRequest, VideoGenResult, VideoProvider


def test_request_defaults():
    r = VideoGenRequest(prompt="a cat")
    assert r.prompt == "a cat"
    assert r.aspect_ratio == "16:9"
    assert r.duration_s == 8.0
    assert r.init_image_path is None


def test_result_fields():
    res = VideoGenResult(video_path="/tmp/x.mp4", duration_ms=8000)
    assert res.video_path == "/tmp/x.mp4"
    assert res.duration_ms == 8000


def test_provider_is_abstract():
    assert inspect.isabstract(VideoProvider)
    with pytest.raises(TypeError):
        VideoProvider()
