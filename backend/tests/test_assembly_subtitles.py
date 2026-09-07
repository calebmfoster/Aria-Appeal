import pytest

from app.services.video.assembly import Beat, build_ass


def _beat(start_ms, audio_ms, text, window_ms=None):
    return Beat(
        clip_path="/clips/a.mp4",
        audio_path="/audio/a.wav" if audio_ms else None,
        text=text,
        start_ms=start_ms,
        window_ms=window_ms if window_ms is not None else max(audio_ms, 1000),
        audio_ms=audio_ms,
        pad_ms=0,
        trim_start_ms=0,
        trim_end_ms=None,
    )


def _dialogues(ass: str):
    return [ln for ln in ass.splitlines() if ln.startswith("Dialogue:")]


def test_one_dialogue_line_per_voiced_beat():
    beats = [_beat(0, 2000, "one"), _beat(2000, 3000, "two")]
    lines = _dialogues(build_ass(beats, {"enabled": True}))
    assert len(lines) == 2
    assert "one" in lines[0] and "two" in lines[1]


def test_cue_ends_with_narration_not_window():
    """A caption must clear during a long clip's trailing silence."""
    beats = [_beat(0, 2000, "short line", window_ms=5000)]
    line = _dialogues(build_ass(beats, {"enabled": True}))[0]
    # start 0:00:00.00, end 0:00:02.00 — not 5s
    assert "0:00:00.00" in line
    assert "0:00:02.00" in line
    assert "0:00:05.00" not in line


def test_disabled_yields_no_dialogue():
    beats = [_beat(0, 2000, "one")]
    assert _dialogues(build_ass(beats, {"enabled": False})) == []


def test_unvoiced_beat_has_no_cue():
    beats = [_beat(0, 0, "never spoken")]
    assert _dialogues(build_ass(beats, {"enabled": True})) == []


def test_empty_text_has_no_cue():
    beats = [_beat(0, 2000, "   ")]
    assert _dialogues(build_ass(beats, {"enabled": True})) == []


def test_colour_converts_to_ass_bgr():
    """ASS uses &HBBGGRR — reversed from the RRGGBB people write."""
    ass = build_ass([_beat(0, 1000, "x")], {"enabled": True, "color": "FF8000"})
    assert "&H000080FF" in ass


def test_default_colour_is_white():
    ass = build_ass([_beat(0, 1000, "x")], {"enabled": True})
    assert "&H00FFFFFF" in ass


@pytest.mark.parametrize("position,alignment", [("bottom", 2), ("top", 8), ("center", 5)])
def test_position_maps_to_alignment(position, alignment):
    ass = build_ass([_beat(0, 1000, "x")], {"enabled": True, "position": position})
    style = next(ln for ln in ass.splitlines() if ln.startswith("Style:"))
    assert f",{alignment}," in style


def test_font_size_is_applied():
    ass = build_ass([_beat(0, 1000, "x")], {"enabled": True, "font_size": 52})
    style = next(ln for ln in ass.splitlines() if ln.startswith("Style:"))
    assert ",52," in style


def test_commas_and_newlines_do_not_corrupt_dialogue():
    beats = [_beat(0, 2000, "Wait, stop.\nGo now.")]
    lines = _dialogues(build_ass(beats, {"enabled": True}))
    assert len(lines) == 1
    # Dialogue has exactly 9 comma-separated fields before the text, so a comma in
    # the text must survive without adding a field boundary that breaks rendering.
    assert "Wait, stop." in lines[0]
    assert "\\N" in lines[0]
    assert "\n" not in lines[0]


def test_timestamps_format_centiseconds():
    beats = [_beat(65430, 1570, "x")]
    line = _dialogues(build_ass(beats, {"enabled": True}))[0]
    assert "0:01:05.43" in line
    assert "0:01:07.00" in line


def test_has_required_ass_sections():
    ass = build_ass([_beat(0, 1000, "x")], {"enabled": True})
    assert "[Script Info]" in ass
    assert "[V4+ Styles]" in ass
    assert "[Events]" in ass
