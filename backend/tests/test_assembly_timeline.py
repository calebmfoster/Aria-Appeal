import types

import pytest

from app.services.video.assembly import Beat, compute_timeline


def _clip(order, url, duration_ms, trim_start=None, trim_end=None):
    return types.SimpleNamespace(
        sequence_order=order,
        video_url=url,
        duration_ms=duration_ms,
        trim_start_ms=trim_start,
        trim_end_ms=trim_end,
        segment_id=f"seg{order}",
    )


def _segment(order, text, audio_url, start_ms, end_ms):
    return types.SimpleNamespace(
        sequence_order=order,
        text=text,
        audio_url=audio_url,
        start_time_ms=start_ms,
        end_time_ms=end_ms,
        id=f"seg{order}",
    )


CLIP_DIR = "/static_root"
AUDIO_DIR = "/audio"


def test_clip_longer_than_narration_keeps_clip_length():
    clips = [_clip(0, "/static/video/assets/a.mp4", 5000)]
    segs = [_segment(0, "hello", "/static/audio/a.wav", 0, 4800)]
    beats = compute_timeline(clips, segs, CLIP_DIR, AUDIO_DIR)

    assert len(beats) == 1
    b = beats[0]
    assert b.window_ms == 5000
    assert b.audio_ms == 4800
    assert b.pad_ms == 0


def test_narration_longer_than_clip_pads_video():
    clips = [_clip(0, "/static/video/assets/a.mp4", 3000)]
    segs = [_segment(0, "a long line", "/static/audio/a.wav", 0, 4500)]
    beats = compute_timeline(clips, segs, CLIP_DIR, AUDIO_DIR)

    b = beats[0]
    assert b.window_ms == 4500
    assert b.audio_ms == 4500
    assert b.pad_ms == 1500


def test_explicit_trim_shortens_the_window():
    clips = [_clip(0, "/static/video/assets/a.mp4", 8000, trim_start=1000, trim_end=4000)]
    segs = [_segment(0, "x", "/static/audio/a.wav", 0, 2000)]
    beats = compute_timeline(clips, segs, CLIP_DIR, AUDIO_DIR)

    b = beats[0]
    assert b.trim_start_ms == 1000
    assert b.trim_end_ms == 4000
    assert b.window_ms == 3000  # trimmed clip is 3s, narration 2s


def test_trim_shorter_than_narration_still_pads():
    clips = [_clip(0, "/static/video/assets/a.mp4", 8000, trim_start=0, trim_end=2000)]
    segs = [_segment(0, "x", "/static/audio/a.wav", 0, 3500)]
    beats = compute_timeline(clips, segs, CLIP_DIR, AUDIO_DIR)

    b = beats[0]
    assert b.window_ms == 3500
    assert b.pad_ms == 1500


def test_starts_are_cumulative_and_contiguous():
    clips = [
        _clip(0, "/static/video/assets/a.mp4", 5000),
        _clip(1, "/static/video/assets/b.mp4", 3000),
        _clip(2, "/static/video/assets/c.mp4", 4000),
    ]
    segs = [
        _segment(0, "one", "/static/audio/1.wav", 0, 4800),
        _segment(1, "two", "/static/audio/2.wav", 0, 2700),
        _segment(2, "three", "/static/audio/3.wav", 0, 2800),
    ]
    beats = compute_timeline(clips, segs, CLIP_DIR, AUDIO_DIR)

    assert [b.start_ms for b in beats] == [0, 5000, 8000]
    assert beats[-1].start_ms + beats[-1].window_ms == 12000


def test_orders_by_sequence_regardless_of_input_order():
    clips = [
        _clip(2, "/static/video/assets/c.mp4", 1000),
        _clip(0, "/static/video/assets/a.mp4", 1000),
        _clip(1, "/static/video/assets/b.mp4", 1000),
    ]
    segs = [
        _segment(1, "two", "/static/audio/2.wav", 0, 500),
        _segment(0, "one", "/static/audio/1.wav", 0, 500),
        _segment(2, "three", "/static/audio/3.wav", 0, 500),
    ]
    beats = compute_timeline(clips, segs, CLIP_DIR, AUDIO_DIR)
    assert [b.text for b in beats] == ["one", "two", "three"]


def test_clip_without_audio_is_silent_but_present():
    clips = [_clip(0, "/static/video/assets/a.mp4", 4000)]
    segs = [_segment(0, "no audio yet", None, None, None)]
    beats = compute_timeline(clips, segs, CLIP_DIR, AUDIO_DIR)

    b = beats[0]
    assert b.audio_path is None
    assert b.audio_ms == 0
    assert b.window_ms == 4000
    assert b.pad_ms == 0


def test_clip_path_keeps_its_static_subpath():
    """Clips live in different subdirs by source (assets/clips/uploads), so the
    URL's own subpath must survive — resolving by basename would collapse them."""
    clips = [
        _clip(0, "/static/video/assets/a.mp4", 4000),
        _clip(1, "/static/video/clips/b.mp4", 4000),
    ]
    segs = [
        _segment(0, "x", "/static/audio/a.wav", 0, 1000),
        _segment(1, "y", "/static/audio/b.wav", 0, 1000),
    ]
    beats = compute_timeline(clips, segs, CLIP_DIR, AUDIO_DIR)

    assert beats[0].clip_path.replace("\\", "/") == "/static_root/video/assets/a.mp4"
    assert beats[1].clip_path.replace("\\", "/") == "/static_root/video/clips/b.mp4"
    # Audio is flat in tts_service.output_dir, so it still joins by basename.
    assert beats[0].audio_path.replace("\\", "/") == "/audio/a.wav"


def test_clip_with_no_video_url_is_skipped():
    clips = [_clip(0, None, None), _clip(1, "/static/video/assets/b.mp4", 2000)]
    segs = [
        _segment(0, "one", "/static/audio/1.wav", 0, 500),
        _segment(1, "two", "/static/audio/2.wav", 0, 500),
    ]
    beats = compute_timeline(clips, segs, CLIP_DIR, AUDIO_DIR)
    assert len(beats) == 1
    assert beats[0].text == "two"
    assert beats[0].start_ms == 0


def test_missing_duration_falls_back_to_narration():
    clips = [_clip(0, "/static/video/assets/a.mp4", None)]
    segs = [_segment(0, "x", "/static/audio/a.wav", 0, 2500)]
    beats = compute_timeline(clips, segs, CLIP_DIR, AUDIO_DIR)
    assert beats[0].window_ms == 2500


def test_compute_timeline_records_clip_id():
    """Beats carry the id of the clip they came from, so assemble_project can
    write timeline positions back without re-deriving the filter predicate."""
    from app.services.video.assembly import compute_timeline

    class _C:
        def __init__(self, cid, order, url, duration):
            self.id = cid
            self.sequence_order = order
            self.video_url = url
            self.duration_ms = duration
            self.trim_start_ms = None
            self.trim_end_ms = None
            self.segment_id = None

    clips = [
        _C("c-b", 1, "/static/video/assets/b.mp4", 3000),
        _C("c-a", 0, "/static/video/assets/a.mp4", 2000),
        _C("c-skip", 2, None, 4000),
    ]

    beats = compute_timeline(clips, [], "/root", "/audio")

    assert [b.clip_id for b in beats] == ["c-a", "c-b"]
    assert [b.start_ms for b in beats] == [0, 2000]
    assert [b.window_ms for b in beats] == [2000, 3000]


def test_apply_timeline_positions_writes_back_to_clips():
    """assemble_project uses this to stamp each clip's place on the timeline."""
    from app.services.video.assembly import Beat, apply_timeline_positions

    class _C:
        def __init__(self, cid):
            self.id = cid
            self.timeline_start_ms = None
            self.timeline_end_ms = None

    a, b = _C("c-a"), _C("c-b")
    beats = [
        Beat("p1", None, "", 0, 2000, 0, 0, 0, None, clip_id="c-a"),
        Beat("p2", None, "", 2000, 3000, 0, 0, 0, None, clip_id="c-b"),
    ]

    apply_timeline_positions([a, b], beats)

    assert (a.timeline_start_ms, a.timeline_end_ms) == (0, 2000)
    assert (b.timeline_start_ms, b.timeline_end_ms) == (2000, 5000)


def test_apply_timeline_positions_clears_clips_with_no_beat():
    """A clip with no video_url produces no beat; it must be reset rather than
    left holding a stale position from a previous assembly."""
    from app.services.video.assembly import Beat, apply_timeline_positions

    class _C:
        def __init__(self, cid):
            self.id = cid
            self.timeline_start_ms = 999
            self.timeline_end_ms = 999

    kept, skipped = _C("c-a"), _C("c-skip")
    beats = [Beat("p1", None, "", 0, 2000, 0, 0, 0, None, clip_id="c-a")]

    apply_timeline_positions([kept, skipped], beats)

    assert (kept.timeline_start_ms, kept.timeline_end_ms) == (0, 2000)
    assert (skipped.timeline_start_ms, skipped.timeline_end_ms) == (None, None)
