"""
Voice Cloning Service — extracts acoustic embeddings from reference audio
using the Qwen3-TTS tokenizer, and provides zero-shot synthesis via the Base model.
"""

import os
import uuid
import logging
import numpy as np

try:
    import torch
    import soundfile as sf
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from qwen_tts import Qwen3TTSTokenizer
    TOKENIZER_AVAILABLE = True
except ImportError:
    TOKENIZER_AVAILABLE = False

logger = logging.getLogger(__name__)

VOICE_UPLOADS_DIR = os.path.join(os.getcwd(), "static", "voice_uploads")
os.makedirs(VOICE_UPLOADS_DIR, exist_ok=True)

EMBEDDING_DIM = 1024


class VoiceClonerService:
    """Handles acoustic embedding extraction and storage for voice cloning."""

    def __init__(self):
        self._tokenizer = None
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized:
            return
        if TOKENIZER_AVAILABLE and TORCH_AVAILABLE:
            try:
                from app.core.config import settings
                model_path = getattr(settings, "QWEN_MODEL_PATH", "Qwen/Qwen3-TTS-12Hz-1.7B-Base")
                logger.info(f"Initializing Qwen3-TTS tokenizer from '{model_path}'")
                self._tokenizer = Qwen3TTSTokenizer.from_pretrained(model_path)
                logger.info("Qwen3-TTS tokenizer loaded successfully.")
            except Exception as e:
                logger.warning(f"Failed to load Qwen3-TTS tokenizer: {e}. Embeddings will use fallback.")
                self._tokenizer = None
        else:
            logger.warning("Qwen3-TTS tokenizer dependencies not available. Using fallback embeddings.")
        self._initialized = True

    def save_reference_audio(self, audio_data: bytes, profile_name: str) -> str:
        """
        Saves the uploaded reference audio WAV file to disk as PCM WAV
        (re-encodes if the source uses a non-PCM codec like GSM 6.10).
        Returns the absolute file path.
        """
        import io
        safe_name = "".join(c for c in profile_name if c.isalnum() or c in "-_").strip() or "voice"
        filename = f"{safe_name}_{uuid.uuid4().hex[:8]}.wav"
        file_path = os.path.join(VOICE_UPLOADS_DIR, filename)

        try:
            # Read audio data (handles any codec soundfile supports) and re-write as PCM WAV
            data, samplerate = sf.read(io.BytesIO(audio_data))
            sf.write(file_path, data, samplerate, subtype='PCM_16')
            logger.info(f"Saved reference audio as PCM WAV to: {file_path}")
        except Exception as e:
            # Fallback: save raw bytes then attempt in-place re-encode
            logger.warning(f"Direct re-encode failed ({e}), trying save-then-reencode")
            with open(file_path, "wb") as f:
                f.write(audio_data)
            try:
                data, samplerate = sf.read(file_path)
                sf.write(file_path, data, samplerate, subtype='PCM_16')
                logger.info(f"Re-encoded saved file to PCM WAV: {file_path}")
            except Exception as e2:
                logger.error(f"Could not re-encode audio to PCM WAV: {e2}. File may not be browser-playable.")

        return file_path

    def extract_embedding(self, audio_data: bytes) -> list[float]:
        """
        Extracts a 1024-dimensional acoustic embedding from the reference audio.

        Uses the Qwen3-TTS tokenizer to extract acoustic tokens, then derives
        a fixed-size embedding vector from the token statistics.

        Falls back to a spectral fingerprint if the tokenizer is unavailable.
        """
        self._ensure_initialized()

        if self._tokenizer is not None:
            return self._extract_with_tokenizer(audio_data)
        else:
            return self._extract_spectral_fallback(audio_data)

    def _extract_with_tokenizer(self, audio_data: bytes) -> list[float]:
        """Extract embedding using the actual Qwen3-TTS tokenizer."""
        import io
        try:
            # Load audio
            with io.BytesIO(audio_data) as buf:
                samples, samplerate = sf.read(buf)

            # Convert to mono if stereo
            if len(samples.shape) > 1:
                samples = np.mean(samples, axis=1)

            # Convert to torch tensor
            audio_tensor = torch.tensor(samples, dtype=torch.float32).unsqueeze(0)

            # Extract acoustic tokens via the tokenizer
            with torch.no_grad():
                tokens = self._tokenizer.encode_audio(audio_tensor, sample_rate=samplerate)

            # Derive a fixed-size embedding from the token sequence
            # tokens shape is typically (1, num_codebooks, seq_len)
            if isinstance(tokens, torch.Tensor):
                token_np = tokens.squeeze(0).float().cpu().numpy()
            else:
                token_np = np.array(tokens, dtype=np.float32)

            # Compute statistical embedding: mean + std across time for each codebook
            # Then pad/truncate to EMBEDDING_DIM
            embedding = self._tokens_to_embedding(token_np)
            logger.info(f"Extracted tokenizer embedding with norm={np.linalg.norm(embedding):.4f}")
            return embedding.tolist()

        except Exception as e:
            logger.warning(f"Tokenizer extraction failed: {e}. Using spectral fallback.")
            return self._extract_spectral_fallback(audio_data)

    def _tokens_to_embedding(self, token_array: np.ndarray) -> np.ndarray:
        """
        Convert a variable-length token array into a fixed EMBEDDING_DIM vector.
        Uses mean, std, min, max statistics across the time dimension.
        """
        if token_array.ndim == 1:
            token_array = token_array.reshape(1, -1)

        stats = []
        for stat_fn in [np.mean, np.std, np.min, np.max]:
            stats.append(stat_fn(token_array, axis=-1))

        combined = np.concatenate(stats)

        # Pad or truncate to EMBEDDING_DIM
        if len(combined) >= EMBEDDING_DIM:
            embedding = combined[:EMBEDDING_DIM]
        else:
            embedding = np.zeros(EMBEDDING_DIM, dtype=np.float32)
            embedding[:len(combined)] = combined

        # L2 normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding.astype(np.float32)

    def _extract_spectral_fallback(self, audio_data: bytes) -> list[float]:
        """
        Fallback: compute a spectral fingerprint embedding when the tokenizer
        is unavailable. Uses MFCC-like statistics from the raw audio.
        """
        import io
        try:
            with io.BytesIO(audio_data) as buf:
                samples, samplerate = sf.read(buf)

            if len(samples.shape) > 1:
                samples = np.mean(samples, axis=1)

            # Compute spectrogram via short-time FFT
            from scipy.signal import stft
            _, _, Zxx = stft(samples, fs=samplerate, nperseg=512, noverlap=256)
            magnitude = np.abs(Zxx)

            # Compute mel-like band energies (simplified)
            n_bands = 256
            freq_bins = magnitude.shape[0]
            band_size = max(1, freq_bins // n_bands)

            band_energies = []
            for i in range(n_bands):
                start = i * band_size
                end = min(start + band_size, freq_bins)
                band_energies.append(np.mean(magnitude[start:end, :], axis=0))

            band_matrix = np.array(band_energies)  # (n_bands, time_frames)

            embedding = self._tokens_to_embedding(band_matrix)
            logger.info(f"Extracted spectral fallback embedding with norm={np.linalg.norm(embedding):.4f}")
            return embedding.tolist()

        except Exception as e:
            logger.error(f"Spectral fallback failed: {e}. Returning zero embedding.")
            return [0.0] * EMBEDDING_DIM


# Singleton
voice_cloner = VoiceClonerService()
