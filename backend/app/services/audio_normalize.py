import logging
import numpy as np

logger = logging.getLogger(__name__)


def trim_silence(samples: np.ndarray, sr: int, threshold_db: float = -45.0) -> np.ndarray:
    """Strip leading and trailing silence below threshold_db using 10ms RMS frames."""
    if len(samples) == 0:
        return samples

    frame_size = max(1, int(sr * 0.01))
    thresh_linear = 10 ** (threshold_db / 20.0)
    mono = samples if samples.ndim == 1 else samples.mean(axis=1)

    n_frames = len(mono) // frame_size
    if n_frames == 0:
        return samples

    frames = mono[: n_frames * frame_size].reshape(n_frames, frame_size)
    rms = np.sqrt((frames ** 2).mean(axis=1))

    above = np.where(rms > thresh_linear)[0]
    if len(above) == 0:
        return samples  # all-silent — return as-is to avoid empty output

    start = above[0] * frame_size
    end = min((above[-1] + 1) * frame_size, len(samples))
    return samples[start:end]


def pad_silence(
    samples: np.ndarray, sr: int, head_ms: int = 30, tail_ms: int = 120
) -> np.ndarray:
    """Prepend head_ms and append tail_ms of silence."""
    head_n = int(sr * head_ms / 1000)
    tail_n = int(sr * tail_ms / 1000)

    if samples.ndim == 1:
        head = np.zeros(head_n, dtype=samples.dtype)
        tail = np.zeros(tail_n, dtype=samples.dtype)
    else:
        head = np.zeros((head_n, samples.shape[1]), dtype=samples.dtype)
        tail = np.zeros((tail_n, samples.shape[1]), dtype=samples.dtype)

    return np.concatenate([head, samples, tail])


def normalize_lufs(
    samples: np.ndarray,
    sr: int,
    target_lufs: float = -18.0,
    true_peak_ceiling_db: float = -1.0,
) -> np.ndarray:
    """LUFS-normalize to target_lufs. Falls back to peak normalization for clips <400ms."""
    try:
        import pyloudnorm as pyln
    except ImportError:
        logger.warning("pyloudnorm not available — skipping LUFS normalization")
        return samples

    ceiling = 10 ** (true_peak_ceiling_db / 20.0)

    # pyloudnorm needs at least 400ms (ITU-R BS.1770 block size)
    if len(samples) < int(0.4 * sr):
        peak = np.abs(samples).max()
        if peak > 0:
            return (samples / peak * ceiling).astype(samples.dtype)
        return samples

    meter = pyln.Meter(sr)
    try:
        loudness = meter.integrated_loudness(samples.astype(np.float64))
    except Exception as e:
        logger.warning(f"LUFS measurement failed: {e} — skipping")
        return samples

    if not np.isfinite(loudness):
        logger.warning("LUFS measurement returned non-finite value — skipping")
        return samples

    gain = 10 ** ((target_lufs - loudness) / 20.0)
    result = (samples * gain).astype(samples.dtype)

    # Apply true-peak ceiling
    peak = np.abs(result).max()
    if peak > ceiling:
        result = (result * ceiling / peak).astype(samples.dtype)

    return result


def post_process_segment(samples: np.ndarray, sr: int) -> np.ndarray:
    """Per-segment chain: trim silence → pad silence → LUFS normalize to -18 LUFS."""
    samples = trim_silence(samples, sr)
    if len(samples) == 0:
        return samples
    samples = pad_silence(samples, sr)
    return normalize_lufs(samples, sr, target_lufs=-18.0, true_peak_ceiling_db=-1.0)


def post_process_master(samples: np.ndarray, sr: int) -> np.ndarray:
    """Master-level LUFS pass (no silence trim/pad): normalize to -16 LUFS."""
    return normalize_lufs(samples, sr, target_lufs=-16.0, true_peak_ceiling_db=-1.0)
