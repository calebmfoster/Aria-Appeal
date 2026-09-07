import asyncio
import os
import pytest
from app.services.video.factory import get_video_provider
from app.services.video.asset_provider import AssetVideoProvider
from app.services.video.gemini_provider import GeminiVeoProvider
from app.services.video.local_provider import LocalVideoProvider
from app.services.video.base import VideoGenRequest


def test_asset_source_returns_asset_provider():
    p = get_video_provider("asset")
    assert isinstance(p, AssetVideoProvider)
    assert p.assets_dir.endswith(os.path.join("video", "assets"))


def test_uploaded_source_returns_asset_provider():
    # uploads are resolved the same way as assets (pre-existing files)
    p = get_video_provider("uploaded")
    assert isinstance(p, AssetVideoProvider)
    assert p.assets_dir.endswith(os.path.join("video", "uploads"))


def test_generated_gemini_returns_gemini(monkeypatch):
    from app.core import system_config
    s = system_config.config_manager.get_settings().model_copy(
        update={"video_provider": "gemini", "gemini_api_key": "k", "veo_model": "veo-3.0-generate-001"}
    )
    monkeypatch.setattr(system_config.config_manager, "get_settings", lambda: s)
    p = get_video_provider("generated")
    assert isinstance(p, GeminiVeoProvider)
    assert p.api_key == "k"
    assert p.model == "veo-3.0-generate-001"


def test_generated_local_returns_local(monkeypatch):
    from app.core import system_config
    s = system_config.config_manager.get_settings().model_copy(update={"video_provider": "local"})
    monkeypatch.setattr(system_config.config_manager, "get_settings", lambda: s)
    p = get_video_provider("generated")
    assert isinstance(p, LocalVideoProvider)


def test_unknown_source_type_raises():
    with pytest.raises(ValueError):
        get_video_provider("bogus")


def test_local_provider_not_implemented():
    with pytest.raises(NotImplementedError):
        asyncio.run(LocalVideoProvider().generate(VideoGenRequest(prompt="x")))
