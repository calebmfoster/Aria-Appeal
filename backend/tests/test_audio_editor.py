import os
import pytest
from pydub import AudioSegment
from pydub.generators import Sine
from app.services.audio_editor import audio_editor

def test_splice_audio():
    """
    Verifies that splice_audio correctly replaces a segment and returns a new file.
    """
    # 1. Create dummy master file (5 seconds of 440Hz)
    master_audio = Sine(440).to_audio_segment(duration=5000)
    master_path = "test_master.wav"
    master_audio.export(master_path, format="wav")
    
    # 2. Create dummy segment (1 second of 880Hz)
    segment_audio = Sine(880).to_audio_segment(duration=1000)
    segment_path = "test_segment.wav"
    segment_audio.export(segment_path, format="wav")
    
    # 3. Splice 2000ms - 3000ms
    try:
        output_path = audio_editor.splice_audio(
            master_file_path=master_path,
            new_segment_path=segment_path,
            start_ms=2000,
            end_ms=3000,
            crossfade_ms=50
        )
        
        assert os.path.exists(output_path)
        assert output_path != master_path
        
        # Verify duration
        # Original: 5000ms
        # Removed: 1000ms (2000-3000)
        # Added: 1000ms
        # Crossfades: Might affect duration depending on implementation
        # Our implementation:
        # pre_roll (2000ms) + segment (1000ms) + post_roll (2000ms) = 5000ms
        # Crossfades are fade_in/fade_out, not overlap-add in our current 'simple' implementation.
        # So duration should be exactly 5000ms.
        
        result_audio = AudioSegment.from_file(output_path)
        assert len(result_audio) == 5000
        
    finally:
        # Cleanup
        if os.path.exists(master_path):
            os.remove(master_path)
        if os.path.exists(segment_path):
            os.remove(segment_path)
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)
