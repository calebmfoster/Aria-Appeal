"""Short, cached greeting samples for the voice pickers.

Previews are synthesized through the normal TTS path and cached under the
static audio dir:
  - preview_preset_{Speaker}.wav   — one per preset, shared across all users
  - preview_clone_{profile_id}.wav — one per cloned profile

This replaces the old behaviour of pointing preview_url at the user's raw
uploaded reference clip, which played back their whole original recording
instead of a sample of the cloned voice.
"""
import logging
import os
from typing import Optional

from app.services.tts_engine import tts_service
from app.services.voice_presets import get_preset

logger = logging.getLogger(__name__)

CLONE_GREETING = "Welcome to Aria Appeal."


def preset_preview_filename(speaker: str) -> str:
    return f"preview_preset_{speaker}.wav"


def clone_preview_filename(profile_id) -> str:
    return f"preview_clone_{profile_id}.wav"


def _cache_path(filename: str) -> str:
    return os.path.join(tts_service.output_dir, filename)


def cached_url(filename: str) -> Optional[str]:
    """The served URL if the preview is already on disk, else None."""
    return f"/static/audio/{filename}" if os.path.isfile(_cache_path(filename)) else None


async def _synthesize_into_cache(filename: str, **generate_kwargs) -> Optional[str]:
    """Generate once and move the result to its stable cache name.

    The engine writes to a random uuid filename, so the file is renamed rather
    than regenerated. Returns None if the engine did not actually produce a file.
    """
    existing = cached_url(filename)
    if existing:
        return existing

    try:
        url = await tts_service.generate_audio(**generate_kwargs)
    except Exception:
        logger.exception("Preview synthesis failed for %s", filename)
        return None

    source = os.path.join(tts_service.output_dir, os.path.basename(url or ""))
    if not url or not os.path.isfile(source):
        logger.warning("Preview synthesis produced no file for %s", filename)
        return None

    os.replace(source, _cache_path(filename))
    return f"/static/audio/{filename}"


async def ensure_preset_preview(speaker: str) -> Optional[str]:
    """Preview a preset in ITS OWN language. Raises ValueError for an unknown speaker."""
    preset = get_preset(speaker)
    if preset is None:
        raise ValueError(f"Unknown preset speaker: {speaker}")

    return await _synthesize_into_cache(
        preset_preview_filename(speaker),
        text=preset.greeting,
        voice_profile_id=speaker,
    )


async def ensure_clone_preview(
    profile_id,
    reference_audio_path: Optional[str],
    reference_text: Optional[str],
) -> Optional[str]:
    """Preview a cloned voice by synthesizing the greeting through the clone path."""
    if not reference_audio_path:
        return None

    return await _synthesize_into_cache(
        clone_preview_filename(profile_id),
        text=CLONE_GREETING,
        reference_audio_path=reference_audio_path,
        reference_text=reference_text,
    )


def clone_preview_url(profile_id) -> Optional[str]:
    return cached_url(clone_preview_filename(profile_id))


def delete_clone_preview(profile_id) -> None:
    path = _cache_path(clone_preview_filename(profile_id))
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            logger.warning("Could not delete stale preview %s", path)
