"""Assembles ready clips + segment narration + subtitles into one MP4.

Fitting rule: each beat's window is the LONGER of its clip and its narration.
- Clip longer  -> keep the clip, pad the audio with trailing silence.
- Narration longer -> freeze the clip's last frame to cover the overrun.
Explicit trims from the editor always win over the clip's natural duration.
"""
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Any, List, Optional

from app.services.video import ffmpeg_utils

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
    clip_id: Any = None


def _basename_join(directory: str, url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    return os.path.join(directory, os.path.basename(url))


def _static_join(static_root: str, url: Optional[str]) -> Optional[str]:
    """Map a served URL to a path under the static root.

    Resolves the URL's own subpath rather than its basename, because clips live in
    different subdirs by source: assets/ for pre-made, clips/ for generated,
    uploads/ for user files.
    """
    if not url:
        return None
    rel = url.lstrip("/")
    if rel.startswith("static/"):
        rel = rel[len("static/"):]
    return os.path.join(static_root, *rel.split("/"))


def _narration_ms(segment) -> int:
    if segment is None or not getattr(segment, "audio_url", None):
        return 0
    start = getattr(segment, "start_time_ms", None) or 0
    end = getattr(segment, "end_time_ms", None) or 0
    return max(0, end - start)


def compute_timeline(clips, segments, static_root: str, audio_dir: str) -> List[Beat]:
    """Lay clips end to end, pairing each with its segment's narration.

    `static_root` is the served static directory; clip URLs resolve beneath it.
    `audio_dir` is flat (tts_service.output_dir), so segment audio joins by basename.

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
            clip_path=_static_join(static_root, clip.video_url),
            audio_path=_basename_join(audio_dir, getattr(segment, "audio_url", None)),
            text=(getattr(segment, "text", "") or "").strip(),
            start_ms=cursor,
            window_ms=window_ms,
            audio_ms=audio_ms,
            pad_ms=max(0, window_ms - clip_ms),
            trim_start_ms=trim_start,
            trim_end_ms=trim_end,
            clip_id=getattr(clip, "id", None),
        ))
        cursor += window_ms

    return beats


def source_fingerprint(segments, subtitle_style: Optional[dict] = None) -> str:
    """Identify the inputs an assembly was built from.

    Stored on video_brief at assembly time and recomputed on read, so the studio
    can tell that the animatic no longer matches the script. Regenerating a
    segment gives it a fresh audio_url, and editing changes the text, so both
    show up here. subtitle_style is included because it changes the burn-in.
    """
    import hashlib
    import json

    h = hashlib.sha256()
    for s in sorted(segments, key=lambda s: getattr(s, "sequence_order", 0)):
        h.update("|".join([
            str(getattr(s, "id", "")),
            getattr(s, "text", "") or "",
            getattr(s, "audio_url", "") or "",
        ]).encode("utf-8"))
        h.update(b"\x00")
    h.update(json.dumps(subtitle_style or {}, sort_keys=True).encode("utf-8"))
    return h.hexdigest()


def apply_timeline_positions(clips, beats: List[Beat]) -> None:
    """Stamp each clip with where it lands on the assembled timeline.

    Clips that produced no beat (no video_url) are reset to None rather than
    left holding a stale position from a previous assembly.
    """
    by_id = {b.clip_id: b for b in beats if b.clip_id is not None}
    for clip in clips:
        beat = by_id.get(getattr(clip, "id", None))
        if beat is None:
            clip.timeline_start_ms = None
            clip.timeline_end_ms = None
        else:
            clip.timeline_start_ms = beat.start_ms
            clip.timeline_end_ms = beat.start_ms + beat.window_ms


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


def _run(cmd, cwd=None):
    subprocess.run(cmd, check=True, capture_output=True, cwd=cwd)


def _concat_list(work_dir: str, name: str, parts: List[str]) -> str:
    """Write a concat-demuxer list of RELATIVE names, so ffmpeg runs with cwd set
    to work_dir and we never have to escape Windows paths."""
    path = os.path.join(work_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        for part in parts:
            f.write(f"file '{os.path.basename(part)}'\n")
    return path


def _prepare_video(beat: Beat, work_dir: str, index: int) -> str:
    """trim -> normalize -> freeze-pad, so every part is codec-identical for concat."""
    stem = f"v{index:03d}"
    current = beat.clip_path

    if beat.trim_start_ms or beat.trim_end_ms is not None:
        trimmed = os.path.join(work_dir, f"{stem}_trim.mp4")
        current = ffmpeg_utils.trim_clip(current, trimmed, beat.trim_start_ms, beat.trim_end_ms)

    normalized = os.path.join(work_dir, f"{stem}_norm.mp4")
    current = ffmpeg_utils.normalize_clip(current, normalized)

    if beat.pad_ms > 0:
        padded = os.path.join(work_dir, f"{stem}_pad.mp4")
        current = ffmpeg_utils.freeze_pad_clip(current, padded, beat.pad_ms)

    final = os.path.join(work_dir, f"{stem}.mp4")
    if os.path.abspath(current) != os.path.abspath(final):
        shutil.move(current, final)
    return final


def _prepare_audio(beat: Beat, work_dir: str, index: int) -> str:
    out = os.path.join(work_dir, f"a{index:03d}.wav")
    if beat.audio_path and os.path.exists(beat.audio_path):
        return ffmpeg_utils.pad_audio(beat.audio_path, out, beat.window_ms)
    return ffmpeg_utils.silent_audio(out, beat.window_ms)


def assemble(beats: List[Beat], out_path: str, style: Optional[dict] = None,
             work_dir: Optional[str] = None) -> str:
    """Fit, concatenate, mux narration and burn captions into one MP4."""
    if not beats:
        raise ValueError("Cannot assemble a video with no beats.")

    ff = ffmpeg_utils._require(ffmpeg_utils.resolve_ffmpeg(), "ffmpeg")

    temp_created = work_dir is None
    work_dir = work_dir or tempfile.mkdtemp(prefix="aria_assembly_")
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)

    try:
        video_parts = [_prepare_video(b, work_dir, i) for i, b in enumerate(beats)]
        audio_parts = [_prepare_audio(b, work_dir, i) for i, b in enumerate(beats)]

        _concat_list(work_dir, "video.txt", video_parts)
        _concat_list(work_dir, "audio.txt", audio_parts)

        _run([ff, "-y", "-f", "concat", "-safe", "0", "-i", "video.txt",
              "-c", "copy", "track_video.mp4"], cwd=work_dir)
        _run([ff, "-y", "-f", "concat", "-safe", "0", "-i", "audio.txt",
              "-c", "copy", "track_audio.wav"], cwd=work_dir)

        ass = build_ass(beats, style)
        has_captions = "Dialogue:" in ass
        with open(os.path.join(work_dir, "subs.ass"), "w", encoding="utf-8") as f:
            f.write(ass)

        cmd = [ff, "-y", "-i", "track_video.mp4", "-i", "track_audio.wav"]
        if has_captions:
            # Relative filename + cwd=work_dir avoids the filtergraph path-escaping
            # problem on Windows (drive colons and backslashes both break it).
            cmd += ["-vf", "subtitles=subs.ass"]
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-shortest", "muxed.mp4"]
        _run(cmd, cwd=work_dir)

        shutil.move(os.path.join(work_dir, "muxed.mp4"), out_path)
        return out_path
    finally:
        if temp_created:
            shutil.rmtree(work_dir, ignore_errors=True)


def static_root() -> str:
    """Mirrors the static mount in main.py."""
    from app.core.config import settings as app_settings
    base = app_settings.STATIC_AUDIO_DIR
    return os.path.dirname(base) if base else os.path.join(os.getcwd(), "static")


async def assemble_project(db, project_id) -> str:
    """Build the animatic for a project and record it on video_brief.

    Returns the served URL of the assembled MP4.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.project import Project
    from app.models.script_segment import ScriptSegment
    from app.models.video_clip import VideoClip
    from app.services.tts_engine import tts_service

    stmt = select(Project).where(Project.id == project_id).options(
        selectinload(Project.segments), selectinload(Project.video_clips)
    )
    project = (await db.execute(stmt)).scalars().first()
    if project is None:
        raise ValueError(f"Project {project_id} not found")

    root = static_root()
    beats = compute_timeline(
        project.video_clips, project.segments, root, tts_service.output_dir
    )
    if not beats:
        raise ValueError("No ready clips to assemble.")

    missing = [b.clip_path for b in beats if not os.path.exists(b.clip_path)]
    if missing:
        raise ValueError(f"Clip files missing on disk: {missing}")

    filename = f"animatic_{project_id}.mp4"
    out_path = os.path.join(root, "video", filename)
    assemble(beats, out_path, project.subtitle_style or {})

    url = f"/static/video/{filename}"
    apply_timeline_positions(project.video_clips, beats)
    brief = dict(project.video_brief or {})
    brief["video_master_url"] = url
    brief["video_source_fingerprint"] = source_fingerprint(
        project.segments, project.subtitle_style
    )
    project.video_brief = brief
    await db.commit()
    return url
