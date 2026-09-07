import asyncio
import pytest
from app.services.video.asset_provider import AssetVideoProvider
from app.services.video.base import VideoGenRequest


def test_resolves_existing_asset(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    f = assets / "clip1.mp4"
    f.write_bytes(b"not a real mp4 but a file")

    p = AssetVideoProvider(assets_dir=str(assets))
    res = asyncio.run(p.generate(VideoGenRequest(prompt="clip1.mp4")))
    assert res.video_path == str(f)


def test_missing_asset_raises(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    p = AssetVideoProvider(assets_dir=str(assets))
    with pytest.raises(FileNotFoundError):
        asyncio.run(p.generate(VideoGenRequest(prompt="nope.mp4")))


def test_path_traversal_is_stripped(tmp_path):
    """`prompt` is attacker-adjacent (it comes from stored clip rows), so the
    provider must never resolve outside assets_dir."""
    assets = tmp_path / "assets"
    assets.mkdir()
    outside = tmp_path / "secret.mp4"
    outside.write_bytes(b"should not be reachable")

    p = AssetVideoProvider(assets_dir=str(assets))
    with pytest.raises(FileNotFoundError):
        asyncio.run(p.generate(VideoGenRequest(prompt="../secret.mp4")))
