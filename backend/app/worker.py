from app.core.config import settings

import asyncio
import os
from app.services.tts_engine import tts_service

from app.services.audio_editor import audio_editor


def generate_audio_task(
    text: str,
    voice_profile_id: str = None,
    emotion: str = None,
    reference_audio_path: str = None,
    reference_text: str = None,
    pitch_shift: float = 0.0,
) -> str:
    print(f"Starting generate_audio_task with text: {text[:20]}...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        print(f"Entering run_until_complete...")
        result = loop.run_until_complete(tts_service.generate_audio(
            text,
            voice_profile_id,
            emotion,
            reference_audio_path=reference_audio_path,
            reference_text=reference_text,
            pitch_shift=pitch_shift,
        ))
        print(f"Completed generation. Result: {result}")
        return result
    except Exception as e:
        print(f"Exception in generate_audio_task: {e}")
        raise
    finally:
        loop.close()
        print(f"Event loop closed.")


def regenerate_audio_task(
    master_file_url: str,
    new_text: str,
    start_ms: int,
    end_ms: int,
    voice_profile_id: str = None,
    emotion: str = None,
    reference_audio_path: str = None,
    reference_text: str = None,
) -> str:
    """
    Regenerates a specific segment of audio and splices it into the master file.
    """
    # 1. Generate new audio segment
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        duration_ms = max(0, end_ms - start_ms)
        new_segment_path_url = loop.run_until_complete(tts_service.generate_audio(
            new_text,
            voice_profile_id,
            emotion,
            duration_ms,
            reference_audio_path=reference_audio_path,
            reference_text=reference_text,
        ))
    except Exception as e:
        print(f"Exception in regenerate_audio_task: {e}")
        raise
    finally:
        loop.close()

    # Convert URL to file path (assuming local static files)
    filename = new_segment_path_url.split("/")[-1]
    new_segment_path = os.path.join(tts_service.output_dir, filename)

    # If there is no master file yet, we can't splice. Just return the new segment.
    if not master_file_url:
        return new_segment_path_url

    # Master file path
    master_filename = master_file_url.split("/")[-1]
    master_file_path = os.path.join(tts_service.output_dir, master_filename)

    # 2. Splice
    new_master_path = audio_editor.splice_audio(
        master_file_path=master_file_path,
        new_segment_path=new_segment_path,
        start_ms=start_ms,
        end_ms=end_ms
    )

    # 3. Return new URL
    new_master_filename = os.path.basename(new_master_path)
    return f"/static/audio/{new_master_filename}"
