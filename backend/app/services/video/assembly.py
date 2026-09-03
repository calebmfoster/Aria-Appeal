"""Assembles ready clips + segment narration + subtitles into one MP4.

Fitting rule: each beat's window is the LONGER of its clip and its narration.
- Clip longer  -> keep the clip, pad the audio with trailing silence.
- Narration longer -> freeze the clip's last frame to cover the overrun.
Explicit trims from the editor always win over the clip's natural duration.
"""
import os
from dataclasses import dataclass
from typing import List, Optional

# ASS alignment codes (numpad layout): 2 = bottom centre, 8 = top, 5 = middle.
_ALIGNMENT = {"bottom": 2, "top": 8, "center": 5}
_DEFAULT_COLOR = "FFFFFF"


@dataclass
class Beat:
    clip_path: str
    audio_path: Optional[str]
    text: str
    start_ms: int
    window_ms: int
    audio_ms: int
    pad_ms: int
    trim_start_ms: int
    trim_end_ms: Optional[int]


def _basename_join(directory: str, url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    return os.path.join(directory, os.path.basename(url))


def _narration_ms(segment) -> int:
    if segment is None or not getattr(segment, "audio_url", None):
        return 0
    start = getattr(segment, "start_time_ms", None) or 0
    end = getattr(segment, "end_time_ms", None) or 0
    return max(0, end - start)


def compute_timeline(clips, segments, clip_dir: str, audio_dir: str) -> List[Beat]:
    """Lay clips end to end, pairing each with its segment's narration.

    Pure: no ffmpeg, no DB, no filesystem access beyond joining paths.
    """
    by_segment = {getattr(s, "id", None): s for s in segments}
    by_order = {getattr(s, "sequence_order", None): s for s in segments}

    beats: List[Beat] = []
    cursor = 0

    for clip in sorted(clips, key=lambda c: c.sequence_order):
        if not getattr(clip, "video_url", None):
            continue  # nothing to show; skip rather than emit a black hole

        segment = by_segment.get(getattr(clip, "segment_id", None))
        if segment is None:
            segment = by_order.get(clip.sequence_order)

        trim_start = clip.trim_start_ms or 0
        trim_end = clip.trim_end_ms

        natural = clip.duration_ms or 0
        if trim_end is not None:
            clip_ms = max(0, trim_end - trim_start)
        elif natural:
            clip_ms = max(0, natural - trim_start)
        else:
            clip_ms = 0

        audio_ms = _narration_ms(segment)
        window_ms = max(clip_ms, audio_ms)

        beats.append(Beat(
            clip_path=_basename_join(clip_dir, clip.video_url),
            audio_path=_basename_join(audio_dir, getattr(segment, "audio_url", None)),
            text=(getattr(segment, "text", "") or "").strip(),
            start_ms=cursor,
            window_ms=window_ms,
            audio_ms=audio_ms,
            pad_ms=max(0, window_ms - clip_ms),
            trim_start_ms=trim_start,
            trim_end_ms=trim_end,
        ))
        cursor += window_ms

    return beats


def _ass_timestamp(ms: int) -> str:
    """H:MM:SS.cc — ASS uses centiseconds, not milliseconds."""
    ms = max(0, int(ms))
    cs = round(ms / 10)
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _ass_color(rrggbb: Optional[str]) -> str:
    """ASS wants &HAABBGGRR — byte order reversed from the RRGGBB people write."""
    value = (rrggbb or _DEFAULT_COLOR).strip().lstrip("#")
    if len(value) != 6:
        value = _DEFAULT_COLOR
    try:
        int(value, 16)
    except ValueError:
        value = _DEFAULT_COLOR
    rr, gg, bb = value[0:2], value[2:4], value[4:6]
    return f"&H00{bb}{gg}{rr}".upper()


def _ass_text(text: str) -> str:
    """Collapse newlines to ASS line breaks; the Dialogue text field is last, so
    commas inside it are safe, but a literal newline would break the line."""
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", r"\N")


def build_ass(beats: List[Beat], style: Optional[dict] = None) -> str:
    """Render burned-in captions as ASS so subtitle_style can drive the look."""
    style = style or {}
    enabled = style.get("enabled", True)
    font_size = int(style.get("font_size", 36))
    alignment = _ALIGNMENT.get(style.get("position", "bottom"), 2)
    primary = _ass_color(style.get("color"))

    head = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "PlayResX: 1920",
        "PlayResY: 1080",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,Arial,{font_size},{primary},&H000000FF,&H00000000,&H80000000,"
        f"0,0,0,0,100,100,0,0,1,3,1,{alignment},80,80,60,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    events = []
    if enabled:
        for beat in beats:
            if beat.audio_ms <= 0 or not beat.text.strip():
                continue  # a caption with nothing spoken under it is noise
            start = _ass_timestamp(beat.start_ms)
            end = _ass_timestamp(beat.start_ms + beat.audio_ms)
            events.append(
                f"Dialogue: 0,{start},{end},Default,,0,0,0,,{_ass_text(beat.text)}"
            )

    return "\n".join(head + events) + "\n"
