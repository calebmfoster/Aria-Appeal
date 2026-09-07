import os

from app.core.config import settings as app_settings
from app.core.system_config import config_manager
from app.services.video.base import VideoProvider
from app.services.video.asset_provider import AssetVideoProvider
from app.services.video.gemini_provider import GeminiVeoProvider
from app.services.video.local_provider import LocalVideoProvider

# Pre-existing files on disk, resolved the same way; only the subdir differs.
_FILE_SOURCES = {"asset": "assets", "uploaded": "uploads"}


def _static_video_dir(sub: str) -> str:
    # Mirrors the static mount in main.py: STATIC_AUDIO_DIR's parent is the
    # static root (set when launching from a worktree), else cwd/static.
    base = app_settings.STATIC_AUDIO_DIR
    root = os.path.dirname(base) if base else os.path.join(os.getcwd(), "static")
    return os.path.join(root, "video", sub)


def get_video_provider(source_type: str) -> VideoProvider:
    """Resolve a provider for a clip's source_type.

    - 'asset' / 'uploaded' -> AssetVideoProvider (pre-existing files on disk)
    - 'generated'          -> the configured generated backend (gemini | local)

    Unknown values raise rather than defaulting to 'generated': falling through
    to Veo would turn a typo into a billed API call.
    """
    if source_type in _FILE_SOURCES:
        return AssetVideoProvider(assets_dir=_static_video_dir(_FILE_SOURCES[source_type]))

    if source_type != "generated":
        raise ValueError(
            f"Unknown video source_type {source_type!r}. "
            f"Expected one of: generated, {', '.join(sorted(_FILE_SOURCES))}."
        )

    s = config_manager.get_settings()
    if s.video_provider == "local":
        return LocalVideoProvider()
    return GeminiVeoProvider(
        api_key=s.gemini_api_key,
        model=s.veo_model,
        out_dir=_static_video_dir("clips"),
    )
