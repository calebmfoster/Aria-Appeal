import os
import logging
from pydub import AudioSegment

logger = logging.getLogger(__name__)

class AudioEditor:
    def __init__(self):
        pass

    def splice_audio(self, master_file_path: str, new_segment_path: str, start_ms: int, end_ms: int, crossfade_ms: int = 25) -> str:
        """
        Replaces a segment of audio in the master file with a new segment.
        Applies a logarithmic crossfade at the stitch points.
        Returns the path to the updated master file.
        """
        try:
            # Load master audio
            master = AudioSegment.from_file(master_file_path)
            
            # Load new segment
            new_segment = AudioSegment.from_file(new_segment_path)
            
            # 1. Create the pre-roll (start of file to insertion point)
            # Apply fade out at the end of pre-roll for smooth transition
            pre_roll = master[:start_ms].fade_out(crossfade_ms)
            
            # 2. Create the post-roll (end of insertion point to end of file)
            # Apply fade in at the start of post-roll
            post_roll = master[end_ms:].fade_in(crossfade_ms)
            
            # 3. Prepare new segment
            # Apply fade in at start and fade out at end to match
            segment_faded = new_segment.fade_in(crossfade_ms).fade_out(crossfade_ms)
            
            # 4. Concatenate
            # Note: We use crossfade concatenation if possible, but manual fading + append is safer for strict timing
            # Let's try simple concatenation first since we manually faded
            final_audio = pre_roll + segment_faded + post_roll
            
            # Export
            # Overwrite original or create new? Let's create new to be safe and return it
            # But the requirement might be to update the state.
            # Let's overwrite for now or return a new filename.
            
            dir_name = os.path.dirname(master_file_path)
            base_name = os.path.basename(master_file_path)
            name, ext = os.path.splitext(base_name)
            new_filename = f"{name}_updated{ext}"
            output_path = os.path.join(dir_name, new_filename)
            
            final_audio.export(output_path, format="wav") # simplified format handling
            
            return output_path

        except Exception as e:
            logger.error(f"Error splicing audio: {e}")
            raise e

audio_editor = AudioEditor()
