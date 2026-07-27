from app.services.video.base import VideoProvider, VideoGenRequest, VideoGenResult


class LocalVideoProvider(VideoProvider):
    """Placeholder for future on-prem generation (company hardware)."""

    name = "local"

    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        raise NotImplementedError(
            "Local video generation is not implemented yet. Use the Gemini provider."
        )
