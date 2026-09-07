"""Tests follow the repo's existing async convention: asyncio.run() inside a
sync test, rather than adding a pytest-asyncio dependency."""
import asyncio
import uuid

import pytest

from app.services import voice_preview


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    d = tmp_path / "audio"
    d.mkdir()
    monkeypatch.setattr(voice_preview.tts_service, "output_dir", str(d))
    return d


def test_preset_preview_filename_is_stable_and_shared_across_users():
    assert voice_preview.preset_preview_filename("Aiden") == "preview_preset_Aiden.wav"
    assert voice_preview.preset_preview_filename("Ono_Anna") == "preview_preset_Ono_Anna.wav"


def test_clone_preview_filename_is_keyed_by_profile_id():
    pid = uuid.UUID("11111111-2222-3333-4444-555555555555")
    assert voice_preview.clone_preview_filename(pid) == (
        "preview_clone_11111111-2222-3333-4444-555555555555.wav"
    )


def test_cached_url_is_none_when_the_file_is_absent(cache_dir):
    assert voice_preview.cached_url("preview_preset_Aiden.wav") is None


def test_cached_url_is_returned_when_the_file_exists(cache_dir):
    (cache_dir / "preview_preset_Aiden.wav").write_bytes(b"RIFF")
    assert voice_preview.cached_url("preview_preset_Aiden.wav") == (
        "/static/audio/preview_preset_Aiden.wav"
    )


def test_ensure_preset_preview_synthesizes_the_native_greeting(cache_dir, monkeypatch):
    calls = {}

    async def fake_generate(text, voice_profile_id=None, **kw):
        calls["text"] = text
        calls["voice"] = voice_profile_id
        name = f"{uuid.uuid4()}.wav"
        (cache_dir / name).write_bytes(b"RIFF-generated")
        return f"/static/audio/{name}"

    monkeypatch.setattr(voice_preview.tts_service, "generate_audio", fake_generate)

    url = asyncio.run(voice_preview.ensure_preset_preview("Ono_Anna"))

    assert url == "/static/audio/preview_preset_Ono_Anna.wav"
    assert (cache_dir / "preview_preset_Ono_Anna.wav").read_bytes() == b"RIFF-generated"
    assert calls["voice"] == "Ono_Anna"
    assert "ようこそ" in calls["text"]


def test_ensure_preset_preview_reuses_the_cache(cache_dir, monkeypatch):
    (cache_dir / "preview_preset_Aiden.wav").write_bytes(b"RIFF-cached")

    async def boom(*_a, **_k):
        raise AssertionError("should not re-synthesize a cached preview")

    monkeypatch.setattr(voice_preview.tts_service, "generate_audio", boom)

    url = asyncio.run(voice_preview.ensure_preset_preview("Aiden"))

    assert url == "/static/audio/preview_preset_Aiden.wav"


def test_ensure_preset_preview_rejects_an_unknown_speaker(cache_dir):
    with pytest.raises(ValueError):
        asyncio.run(voice_preview.ensure_preset_preview("Nobody"))


def test_ensure_clone_preview_uses_the_reference_audio(cache_dir, monkeypatch):
    pid = uuid.uuid4()
    captured = {}

    async def fake_generate(text, voice_profile_id=None, reference_audio_path=None,
                            reference_text=None, **kw):
        captured.update(text=text, ref=reference_audio_path, ref_text=reference_text)
        name = f"{uuid.uuid4()}.wav"
        (cache_dir / name).write_bytes(b"RIFF-clone")
        return f"/static/audio/{name}"

    monkeypatch.setattr(voice_preview.tts_service, "generate_audio", fake_generate)

    url = asyncio.run(voice_preview.ensure_clone_preview(
        pid, reference_audio_path="/refs/caleb.wav", reference_text="hello"
    ))

    assert url == f"/static/audio/preview_clone_{pid}.wav"
    assert captured["ref"] == "/refs/caleb.wav"
    assert captured["ref_text"] == "hello"
    assert captured["text"] == "Welcome to Aria Appeal."


def test_ensure_clone_preview_returns_none_without_reference_audio(cache_dir):
    assert asyncio.run(voice_preview.ensure_clone_preview(uuid.uuid4(), None, None)) is None


def test_a_failed_synthesis_leaves_no_partial_cache_file(cache_dir, monkeypatch):
    async def fake_generate(*_a, **_k):
        # engine returned a path it did not actually create
        return "/static/audio/never-written.wav"

    monkeypatch.setattr(voice_preview.tts_service, "generate_audio", fake_generate)

    url = asyncio.run(voice_preview.ensure_preset_preview("Ryan"))

    assert url is None
    assert not (cache_dir / "preview_preset_Ryan.wav").exists()


def test_a_raising_engine_is_swallowed_and_reported_as_no_preview(cache_dir, monkeypatch):
    async def fake_generate(*_a, **_k):
        raise RuntimeError("CUDA out of memory")

    monkeypatch.setattr(voice_preview.tts_service, "generate_audio", fake_generate)

    assert asyncio.run(voice_preview.ensure_preset_preview("Ryan")) is None


def test_delete_clone_preview_removes_the_cached_file(cache_dir):
    pid = uuid.uuid4()
    path = cache_dir / voice_preview.clone_preview_filename(pid)
    path.write_bytes(b"RIFF")

    voice_preview.delete_clone_preview(pid)

    assert not path.exists()


def test_delete_clone_preview_is_a_no_op_when_nothing_is_cached(cache_dir):
    voice_preview.delete_clone_preview(uuid.uuid4())  # must not raise
