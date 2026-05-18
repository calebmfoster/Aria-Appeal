import os
import io
import wave
import numpy as np
import pyloudnorm as pyln
import webrtcvad
import soundfile as sf
import scipy.signal
import logging

logger = logging.getLogger(__name__)

class VoiceValidator:
    def __init__(self, sample_rate: int = 16000, frame_duration_ms: int = 30):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.vad = webrtcvad.Vad(2)  # Aggressiveness mode 2

    def validate_audio(self, audio_data: bytes, target_lufs: float = -23.0) -> dict:
        """
        Validates audio quality based on LUFS levels and Voice Activity Detection (VAD).
        Returns a dictionary with validation results.
        """
        try:
            # Load audio using soundfile
            with io.BytesIO(audio_data) as buf:
                samples, samplerate = sf.read(buf)
            
            # 1. Check LUFS level
            # pyloudnorm expects (num_samples, num_channels)
            meter = pyln.Meter(samplerate)
            try:
                lufs = meter.integrated_loudness(samples)
            except Exception as e:
                logger.error(f"pyloudnorm error: {e}")
                lufs = -100.0
            
            # 2. VAD check
            # webrtcvad requirements: 16-bit PCM, mono, 8/16/32/48kHz
            # If multi-channel, convert to mono for VAD
            if len(samples.shape) > 1:
                vad_samples_fp = np.mean(samples, axis=1)
            else:
                vad_samples_fp = samples
                
            # Resample to 16kHz if necessary
            vad_rate = samplerate
            if vad_rate not in [8000, 16000, 32000, 48000]:
                logger.warning(f"Resampling from {vad_rate} to 16000 for VAD")
                num_samples = int(len(vad_samples_fp) * 16000 / vad_rate)
                vad_samples_fp = scipy.signal.resample(vad_samples_fp, num_samples)
                vad_rate = 16000
            
            # Convert to 16-bit PCM
            vad_samples_int16 = (vad_samples_fp * 32767).astype(np.int16)
            vad_raw = vad_samples_int16.tobytes()
            
            # Each frame must be 10, 20, or 30ms
            frame_size = int(vad_rate * self.frame_duration_ms / 1000) * 2 # 2 bytes per sample
            frames = []
            for i in range(0, len(vad_raw) - frame_size, frame_size):
                frames.append(vad_raw[i:i + frame_size])
            
            voiced_frames = 0
            for frame in frames:
                if self.vad.is_speech(frame, vad_rate):
                    voiced_frames += 1
            
            speech_ratio = voiced_frames / len(frames) if frames else 0
            
            # Validation logic
            is_valid = True
            errors = []
            
            if lufs < target_lufs - 15: # Threshold of -38 LUFS if target is -23
                errors.append(f"Audio level is too low ({lufs:.2f} LUFS).")
                is_valid = False
            
            if speech_ratio < 0.15: # At least 15% of the audio should be speech
                errors.append(f"Too little speech detected ({speech_ratio*100:.1f}%).")
                is_valid = False
                
            return {
                "is_valid": is_valid,
                "lufs": lufs,
                "speech_ratio": speech_ratio,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Error validating audio: {e}")
            return {
                "is_valid": False,
                "errors": [f"Validation failed: {str(e)}"]
            }

voice_validator = VoiceValidator()
