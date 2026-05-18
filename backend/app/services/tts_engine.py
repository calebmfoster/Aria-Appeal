import os
import uuid
import logging
from pydub import AudioSegment
from pydub.generators import Sine
from app.core.config import settings

try:
    import torch
    import soundfile as sf
    from qwen_tts import Qwen3TTSModel
    QWEN_AVAILABLE = True
except ImportError:
    QWEN_AVAILABLE = False

logger = logging.getLogger(__name__)


class TTSService:
    # Qwen3-TTS preset speakers (CustomVoice model only)
    PRESET_SPEAKERS = [
        "Aiden", "Ryan", "Vivian", "Serena", "Uncle_Fu",
        "Dylan", "Eric", "Ono_Anna", "Sohee"
    ]

    # Model paths for the dual-model architecture
    CUSTOM_VOICE_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
    BASE_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"

    def __init__(self, mode: str = "mock"):
        self.mode = mode
        self.output_dir = os.path.join(os.getcwd(), "static", "audio")
        os.makedirs(self.output_dir, exist_ok=True)

        self.preset_model = None   # CustomVoice model for preset speakers
        self.clone_model = None    # Base model for zero-shot voice cloning
        self.device = "cuda" if QWEN_AVAILABLE and torch.cuda.is_available() else "cpu"
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized:
            return
        if self.mode == "qwen-local":
            self._initialize_qwen()
        self._initialized = True

    def _load_model(self, model_path: str):
        """Load a Qwen3-TTS model from the given path."""
        torch_dtype = torch.bfloat16 if self.device == "cuda" else torch.float32
        kwargs = {"dtype": torch_dtype}
        if self.device == "cuda":
            kwargs["device_map"] = "cuda:0"
        return Qwen3TTSModel.from_pretrained(model_path, **kwargs)

    def _initialize_qwen(self):
        if not QWEN_AVAILABLE:
            logger.error("Qwen3-TTS dependencies are not installed. Falling back to mock mode.")
            self.mode = "mock"
            self._initialized = True
            return

        # Load CustomVoice model for preset speakers
        logger.info(f"Initializing CustomVoice model from '{self.CUSTOM_VOICE_MODEL}' on {self.device}")
        try:
            self.preset_model = self._load_model(self.CUSTOM_VOICE_MODEL)
            logger.info("CustomVoice model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load CustomVoice model: {e}.")
            self.preset_model = None

        # Load Base model for zero-shot voice cloning
        logger.info(f"Initializing Base model from '{self.BASE_MODEL}' on {self.device}")
        try:
            self.clone_model = self._load_model(self.BASE_MODEL)
            logger.info("Base model (voice cloning) loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Base model: {e}. Voice cloning will fall back to preset.")
            self.clone_model = None

        if self.preset_model is None and self.clone_model is None:
            logger.error("Neither TTS model loaded. Falling back to mock mode.")
            self.mode = "mock"

    @staticmethod
    def _apply_pitch_shift(file_path: str, semitones: float) -> None:
        """Shift pitch in-place using resampling. Quality is good for ±6 semitones."""
        if abs(semitones) < 0.05:
            return
        import numpy as np
        import soundfile as sf
        from scipy.signal import resample as scipy_resample
        data, sr = sf.read(file_path)
        factor = 2 ** (semitones / 12.0)
        n_orig = len(data)
        n_shifted = max(1, int(round(n_orig / factor)))
        if data.ndim == 1:
            pitched = scipy_resample(data, n_shifted)
            result = scipy_resample(pitched, n_orig)
        else:
            result = np.column_stack([
                scipy_resample(scipy_resample(data[:, i], n_shifted), n_orig)
                for i in range(data.shape[1])
            ])
        sf.write(file_path, result.astype(data.dtype), sr)

    async def generate_audio(
        self,
        text: str,
        voice_profile_id: str = None,
        emotion: str = None,
        duration_ms: int = None,
        reference_audio_path: str = None,
        reference_text: str = None,
        pitch_shift: float = 0.0,
    ) -> str:
        """
        Generates audio from text. Supports three modes:
        1. Mock — sine wave tone for testing
        2. Preset speaker — uses one of the 9 Qwen3-TTS CustomVoice presets
        3. Zero-shot cloning — uses reference audio via the Base model

        Returns the relative URL path to the generated audio file.
        """
        self._ensure_initialized()

        if voice_profile_id is not None:
            voice_profile_id = str(voice_profile_id)

        filename = f"{uuid.uuid4()}.wav"
        file_path = os.path.join(self.output_dir, filename)

        if self.mode == "mock":
            logger.info(f"Generating mock audio for text: '{text[:30]}...' with voice: {voice_profile_id}")
            target_duration = duration_ms if duration_ms and duration_ms > 0 else 2000
            audio = Sine(440).to_audio_segment(duration=target_duration)
            silence = AudioSegment.silent(duration=500)
            final_audio = silence + audio + silence
            final_audio.export(file_path, format="wav")
            return f"/static/audio/{filename}"

        elif self.mode == "qwen-local":
            # Decide whether to use zero-shot cloning or preset speaker
            if reference_audio_path and os.path.isfile(reference_audio_path):
                audio_url = await self._generate_cloned_voice(
                    text, file_path, emotion, reference_audio_path, reference_text
                )
            else:
                audio_url = await self._generate_preset_voice(
                    text, file_path, emotion, voice_profile_id
                )
            if pitch_shift:
                self._apply_pitch_shift(file_path, pitch_shift)
            return audio_url
        else:
            raise ValueError(f"Unknown TTS mode: {self.mode}")

    async def _generate_preset_voice(
        self, text: str, file_path: str, emotion: str = None, voice_profile_id: str = None
    ) -> str:
        """Generate audio using one of the 9 preset Qwen3-TTS speakers."""
        if self.preset_model is None:
            logger.error("CustomVoice model not loaded. Falling back to mock.")
            return await self._fallback_mock(text, emotion)

        logger.info(f"Generating preset voice audio for: '{text[:50]}...'")
        logger.info(f"Emotion/instruct for preset: '{emotion}'")
        try:
            target_speaker = voice_profile_id if voice_profile_id in self.PRESET_SPEAKERS else "Aiden"
            if voice_profile_id and voice_profile_id not in self.PRESET_SPEAKERS:
                logger.warning(f"Voice '{voice_profile_id}' is not a preset. Falling back to Aiden.")

            logger.info(f"Selected TTS Speaker: {target_speaker}")

            wavs, sr = self.preset_model.generate_custom_voice(
                text=text,
                language="Auto",
                speaker=target_speaker,
                instruct=emotion if emotion else ""
            )

            audio_data = wavs[0]
            sf.write(file_path, audio_data, sr)

            filename = os.path.basename(file_path)
            return f"/static/audio/{filename}"

        except Exception as e:
            logger.error(f"Error during preset TTS inference: {e}")
            return await self._fallback_mock(text, emotion)

    async def _generate_cloned_voice(
        self,
        text: str,
        file_path: str,
        emotion: str = None,
        reference_audio_path: str = None,
        reference_text: str = None,
    ) -> str:
        """
        Generate audio using zero-shot voice cloning via the Qwen3-TTS Base model.
        Uses the uploaded reference audio to clone the speaker's voice characteristics.
        """
        if self.clone_model is None:
            logger.warning("Base model not loaded. Falling back to preset voice.")
            return await self._generate_preset_voice(text, file_path, emotion)

        logger.info(f"Generating CLONED voice audio for: '{text[:50]}...'")
        logger.info(f"Reference audio: {reference_audio_path}")
        logger.info(f"Emotion/instruct: '{emotion}' (note: Base model does not natively support instruct — embedding in text)")
        try:
            # Use generate_voice_clone() — accepts file path directly for ref_audio
            # If ref_text is provided, uses ICL mode; otherwise x_vector_only_mode
            use_x_vector_only = not reference_text

            # Base model does not support instruct/emotion — synthesize text as-is.
            wavs, sr = self.clone_model.generate_voice_clone(
                text=text,
                language="Auto",
                ref_audio=reference_audio_path,
                ref_text=reference_text if reference_text else None,
                x_vector_only_mode=use_x_vector_only,
            )

            audio_data = wavs[0]
            sf.write(file_path, audio_data, sr)

            filename = os.path.basename(file_path)
            logger.info(f"Zero-shot cloned audio saved: {filename}")
            return f"/static/audio/{filename}"

        except Exception as e:
            logger.error(f"Error during zero-shot cloning inference: {e}")
            logger.warning("Falling back to preset voice for this request.")
            # Fall back to preset if cloning fails
            return await self._generate_preset_voice(text, file_path, emotion)

    async def _fallback_mock(self, text: str, emotion: str = None) -> str:
        """Temporary mock fallback to prevent infinite recursion."""
        original_mode = self.mode
        self.mode = "mock"
        res = await self.generate_audio(text, None, emotion)
        self.mode = original_mode
        return res


# Singleton instance
tts_service = TTSService(mode=settings.TTS_MODE if hasattr(settings, "TTS_MODE") else "mock")
