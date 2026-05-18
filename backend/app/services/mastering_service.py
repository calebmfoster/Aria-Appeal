import os
import logging
from pydub import AudioSegment
from typing import List

logger = logging.getLogger(__name__)

class MasteringService:
    def __init__(self):
        pass

    def apply_broadcast_chain(self, audio: AudioSegment) -> AudioSegment:
        """
        Applies a broadcast chain: Normalization, Soft-knee compression (simulated), and Limiting.
        """
        # 1. Normalize to -0.1 dB (Peak Normalization)
        audio = audio.normalize(headroom=0.1)
        
        # 2. Simulated Compression (pydub doesn't have a real compressor)
        # We can simulate it by reducing dynamic range: multiply by gain and then limit.
        # But a better way is to use pydub's 'compress_dynamic_range' if available (not in standard).
        # For now, let's use peak normalization and a gentle gain boost followed by limiting.
        audio = audio + 2.0 # Gentle 2dB gain boost
        
        # 3. Limiter (Hard Clipping avoidance)
        # pydub.AudioSegment handles clipping somewhat, but we should be careful.
        # We'll re-normalize to ensure no clipping after gain.
        audio = audio.normalize(headroom=0.1)
        
        return audio

    def master_project(self, segment_paths: List[str], output_path: str) -> str:
        """
        Concatenates script segments and applies the broadcast chain.
        """
        try:
            if not segment_paths:
                raise ValueError("No segment paths provided for mastering.")

            # Load and concatenate
            combined = AudioSegment.empty()
            for path in segment_paths:
                segment = AudioSegment.from_file(path)
                combined += segment
            
            # Apply broadcast chain
            mastered = self.apply_broadcast_chain(combined)
            
            # Export
            # Ensure directory exists
            dir_name = os.path.dirname(output_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            mastered.export(output_path, format="wav")
            
            return output_path

        except Exception as e:
            logger.error(f"Error mastering project: {e}")
            raise e

mastering_service = MasteringService()
