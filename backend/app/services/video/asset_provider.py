import os
from app.services.video.base import VideoProvider, VideoGenRequest, VideoGenResult
from app.services.video import ffmpeg_utils


class AssetVideoProvider(VideoProvider):
    """Returns a pre-placed clip from the assets dir. `req.prompt` is the filename."""

    name = "asset"

    def __init__(self, assets_dir: str):
        self.assets_dir = assets_dir

    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        # basename() also strips any traversal segments — the filename reaches us
        # from stored clip rows, so it must never resolve outside assets_dir.
        filename = os.path.basename(req.prompt or "")
        path = os.path.join(self.assets_dir, filename)
        if not filename or not os.path.exists(path):
            raise FileNotFoundError(f"Asset clip not found: {path}")
        return VideoGenResult(video_path=path, duration_ms=ffmpeg_utils.probe_duration_ms(path))
