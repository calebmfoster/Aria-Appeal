# Voice Previews + Multi-Language Preset Labelling — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every voice preview play a short synthesized greeting in that voice's own language, and relabel the preset picker as deliberate multi-language narration support rather than an unlabelled trap.

**Architecture:** A new `voice_preview` service synthesizes a fixed greeting through the normal TTS path and caches it under `static/audio/` — `preview_preset_{Speaker}.wav` shared across users, `preview_clone_{profile_id}.wav` per cloned profile. `preview_url` stops pointing at the user's raw uploaded reference audio and points at the cache instead. A preset catalogue (speaker, language, gender, native greeting, English gloss) lives on the backend as the source of truth for synthesis and is mirrored on the frontend as display-only labels, so the pickers stay instant.

**Tech Stack:** FastAPI + SQLAlchemy (async) + Pydantic + Qwen3-TTS on the backend; Next.js 15, React 19, Zustand, Jest on the frontend.

---

## Why this exists

Two open issues in `documentation/Open_Issues.md` under "Dashboard — Voice previews":

1. **Cloned voices play back the user's raw uploaded source clip.** `app/schemas/voice_profile.py:34` builds `preview_url` as `/static/voice_uploads/{filename}` — literally the reference audio the user uploaded. Previewing plays their entire original recording, not a sample of the cloned voice.
2. **Preset voices have no preview at all.** Presets have no `reference_audio_path`, so `preview_url` is `None` (`voice_profile.py:29`) and `VoiceList.tsx:195` hides the play button entirely.
3. **The preset picker is majority non-English and unlabelled.** Of the nine Qwen presets only Aiden and Ryan are English. The pickers in `InspectorPanel.tsx:21` and `create-campaign-modal.tsx:33` are currently *restricted* to those two, which hides seven working voices. The decision is to label rather than hide, and present the coverage as a feature.

**Scope boundary — respect this.** This makes the **voice** layer multi-language. Script generation, the studio UI and subtitle rendering stay English-only. Do not build toward full product localisation, do not add an i18n framework, do not translate any UI chrome.

---

## Baseline

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest -q
```

Expected: `5 failed, 81 passed` (or whatever the count is after Plan 5's tasks — the **5 failed** is the part that must not change). Those five are stale Celery-era / pre-refactor tests documented in `Open_Issues.md`. Do not chase them.

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx jest
```

Expected: `6 failed, 1 passed`, all pre-existing in `InspectorPanel.test.tsx` and `ScriptEditor.test.tsx` (they mock the store but not `next-auth/react` / `next/navigation`). Do not fix them.

Environment: bare `python` is NOT on PATH — use `backend/.venv/Scripts/python.exe`. `frontend/package.json` has no `test` script — use `npx jest`.

---

## File Structure

**Backend — create:**

- `backend/app/services/voice_presets.py` — the nine-speaker catalogue: language, gender, native greeting, English gloss.
- `backend/app/services/voice_preview.py` — cache paths and synthesis for preset and clone previews.
- `backend/scripts/warm_voice_previews.py` — pre-generate all preset previews before the demo.
- `backend/tests/test_voice_presets.py`
- `backend/tests/test_voice_preview.py`

**Backend — modify:**

- `backend/app/schemas/voice_profile.py` — `preview_url` points at the cache, not the upload; add preset schemas.
- `backend/app/api/routes/voice_profiles.py` — three new routes; background preview generation on create.

**Frontend — create:**

- `frontend/lib/voicePresets.ts` — display-only mirror of the catalogue, grouped by language.
- `frontend/lib/voicePresets.test.ts`
- `frontend/components/ui/VoicePreviewButton.tsx` — shared play/stop button that lazily requests a preview.

**Frontend — modify:**

- `frontend/components/dashboard/VoiceList.tsx` — show the play button for every profile; lazy-fetch the preview.
- `frontend/components/studio/InspectorPanel.tsx` — grouped picker + preview button.
- `frontend/components/dashboard/create-campaign-modal.tsx` — grouped picker + preview button.

---

## Task 1: The preset catalogue

**Files:**

- Create: `backend/app/services/voice_presets.py`
- Create: `backend/tests/test_voice_presets.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_voice_presets.py`:

```python
import pytest

from app.services.voice_presets import PRESETS, get_preset, ENGLISH_DEFAULT
from app.services.tts_engine import TTSService


def test_catalogue_covers_exactly_the_engine_preset_speakers():
    """Guards against drift: the catalogue and the TTS engine must agree on
    which speakers exist, or a picker entry synthesizes to an Aiden fallback."""
    assert {p.speaker for p in PRESETS} == set(TTSService.PRESET_SPEAKERS)


def test_only_aiden_and_ryan_are_english():
    english = {p.speaker for p in PRESETS if p.language == "en"}
    assert english == {"Aiden", "Ryan"}


def test_every_preset_has_a_greeting_and_an_english_gloss():
    for p in PRESETS:
        assert p.greeting.strip(), f"{p.speaker} has no greeting"
        assert p.gloss.strip(), f"{p.speaker} has no gloss"


def test_non_english_presets_greet_in_their_own_language():
    """An English sample from a Chinese speaker is the exact bad impression the
    labelling is meant to prevent."""
    for p in PRESETS:
        if p.language != "en":
            assert p.greeting != get_preset("Aiden").greeting


def test_english_presets_use_the_english_greeting():
    assert get_preset("Aiden").greeting == "Welcome to Aria Appeal."
    assert get_preset("Ryan").greeting == "Welcome to Aria Appeal."


def test_languages_covered():
    assert {p.language for p in PRESETS} == {"en", "zh", "ja", "ko"}


def test_get_preset_is_case_sensitive_and_returns_none_for_unknown():
    assert get_preset("Aiden").speaker == "Aiden"
    assert get_preset("Nobody") is None


def test_english_default_is_a_real_english_preset():
    assert get_preset(ENGLISH_DEFAULT).language == "en"
```

- [ ] **Step 2: Run it and watch it fail**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest tests/test_voice_presets.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.voice_presets'`.

- [ ] **Step 3: Implement the catalogue**

Create `backend/app/services/voice_presets.py`:

```python
"""The nine Qwen3-TTS CustomVoice preset speakers, with the language each one
is native to.

Per the Qwen3-TTS-12Hz-1.7B-CustomVoice model card only Aiden and Ryan are
English; the rest are Chinese, Japanese or Korean and read English badly. Qwen's
own guidance is to use each speaker's native language, so previews greet in the
speaker's language and carry an English gloss for the caption.

This is the source of truth for synthesis. frontend/lib/voicePresets.ts mirrors
the display fields; test_voice_presets.py guards both against drift with the
engine's PRESET_SPEAKERS list.
"""
from dataclasses import dataclass
from typing import Optional

ENGLISH_DEFAULT = "Aiden"

_GREETINGS = {
    "en": "Welcome to Aria Appeal.",
    "zh": "欢迎使用 Aria Appeal。",
    "ja": "Aria Appeal へようこそ。",
    "ko": "Aria Appeal에 오신 것을 환영합니다.",
}

_ENGLISH_GLOSS = "Welcome to Aria Appeal."


@dataclass(frozen=True)
class VoicePreset:
    speaker: str
    language: str          # ISO-639-1: en / zh / ja / ko
    language_label: str    # human label for the picker group heading
    gender: str            # "female" | "male"
    accent: Optional[str] = None  # regional note, e.g. "Beijing"

    @property
    def greeting(self) -> str:
        """The preview line, in this speaker's own language."""
        return _GREETINGS[self.language]

    @property
    def gloss(self) -> str:
        """English caption shown next to a non-English preview."""
        return _ENGLISH_GLOSS

    @property
    def label(self) -> str:
        gender = self.gender.capitalize()
        base = f"{self.speaker.replace('_', ' ')} — {gender}"
        return f"{base} ({self.language_label}, {self.accent})" if self.accent \
            else f"{base} ({self.language_label})"


PRESETS = (
    VoicePreset("Aiden", "en", "English", "male"),
    VoicePreset("Ryan", "en", "English", "male"),
    VoicePreset("Vivian", "zh", "Chinese", "female"),
    VoicePreset("Serena", "zh", "Chinese", "female"),
    VoicePreset("Uncle_Fu", "zh", "Chinese", "male"),
    VoicePreset("Dylan", "zh", "Chinese", "male", accent="Beijing"),
    VoicePreset("Eric", "zh", "Chinese", "male", accent="Sichuan"),
    VoicePreset("Ono_Anna", "ja", "Japanese", "female"),
    VoicePreset("Sohee", "ko", "Korean", "female"),
)

_BY_SPEAKER = {p.speaker: p for p in PRESETS}


def get_preset(speaker: str) -> Optional[VoicePreset]:
    return _BY_SPEAKER.get(speaker)
```

- [ ] **Step 4: Run it and watch it pass**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest tests/test_voice_presets.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/voice_presets.py backend/tests/test_voice_presets.py
git commit -m "feat(voice): add preset speaker catalogue with native languages

Only Aiden and Ryan are English; the other seven are Chinese, Japanese or
Korean. Each carries the greeting in its own language plus an English gloss.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: The preview cache service

**Files:**

- Create: `backend/app/services/voice_preview.py`
- Create: `backend/tests/test_voice_preview.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_voice_preview.py`:

```python
import os
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


@pytest.mark.asyncio
async def test_ensure_preset_preview_synthesizes_the_native_greeting(cache_dir, monkeypatch):
    calls = {}

    async def fake_generate(text, voice_profile_id=None, **kw):
        calls["text"] = text
        calls["voice"] = voice_profile_id
        name = f"{uuid.uuid4()}.wav"
        (cache_dir / name).write_bytes(b"RIFF-generated")
        return f"/static/audio/{name}"

    monkeypatch.setattr(voice_preview.tts_service, "generate_audio", fake_generate)

    url = await voice_preview.ensure_preset_preview("Ono_Anna")

    assert url == "/static/audio/preview_preset_Ono_Anna.wav"
    assert (cache_dir / "preview_preset_Ono_Anna.wav").read_bytes() == b"RIFF-generated"
    assert calls["voice"] == "Ono_Anna"
    assert "ようこそ" in calls["text"]


@pytest.mark.asyncio
async def test_ensure_preset_preview_reuses_the_cache(cache_dir, monkeypatch):
    (cache_dir / "preview_preset_Aiden.wav").write_bytes(b"RIFF-cached")

    async def boom(*_a, **_k):
        raise AssertionError("should not re-synthesize a cached preview")

    monkeypatch.setattr(voice_preview.tts_service, "generate_audio", boom)

    url = await voice_preview.ensure_preset_preview("Aiden")

    assert url == "/static/audio/preview_preset_Aiden.wav"


@pytest.mark.asyncio
async def test_ensure_preset_preview_rejects_an_unknown_speaker(cache_dir):
    with pytest.raises(ValueError):
        await voice_preview.ensure_preset_preview("Nobody")


@pytest.mark.asyncio
async def test_ensure_clone_preview_uses_the_reference_audio(cache_dir, monkeypatch):
    pid = uuid.uuid4()
    captured = {}

    async def fake_generate(text, voice_profile_id=None, reference_audio_path=None,
                            reference_text=None, **kw):
        captured.update(text=text, ref=reference_audio_path, ref_text=reference_text)
        name = f"{uuid.uuid4()}.wav"
        (cache_dir / name).write_bytes(b"RIFF-clone")
        return f"/static/audio/{name}"

    monkeypatch.setattr(voice_preview.tts_service, "generate_audio", fake_generate)

    url = await voice_preview.ensure_clone_preview(
        pid, reference_audio_path="/refs/caleb.wav", reference_text="hello"
    )

    assert url == f"/static/audio/preview_clone_{pid}.wav"
    assert captured["ref"] == "/refs/caleb.wav"
    assert captured["ref_text"] == "hello"
    assert captured["text"] == "Welcome to Aria Appeal."


@pytest.mark.asyncio
async def test_ensure_clone_preview_returns_none_without_reference_audio(cache_dir):
    assert await voice_preview.ensure_clone_preview(uuid.uuid4(), None, None) is None


@pytest.mark.asyncio
async def test_a_failed_synthesis_leaves_no_partial_cache_file(cache_dir, monkeypatch):
    async def fake_generate(*_a, **_k):
        return "/static/audio/never-written.wav"  # engine returned a path it did not create

    monkeypatch.setattr(voice_preview.tts_service, "generate_audio", fake_generate)

    url = await voice_preview.ensure_preset_preview("Ryan")

    assert url is None
    assert not (cache_dir / "preview_preset_Ryan.wav").exists()
```

- [ ] **Step 2: Check `pytest-asyncio` is available**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest tests/test_voice_preview.py --collect-only -q
```

If the async tests are reported as skipped or error with "async def functions are not natively supported", install it and register the marker:

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pip install pytest-asyncio
```

Then add to `backend/pytest.ini` (create it if absent, alongside `backend/tests/`):

```ini
[pytest]
asyncio_mode = auto
```

If `pytest.ini` already exists, add only the `asyncio_mode` line under the existing `[pytest]` section. If a `pyproject.toml` or `setup.cfg` already holds the pytest config, put `asyncio_mode = "auto"` there instead rather than creating a competing file.

- [ ] **Step 3: Run it and watch it fail**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest tests/test_voice_preview.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.voice_preview'`.

- [ ] **Step 4: Implement the service**

Create `backend/app/services/voice_preview.py`:

```python
"""Short, cached greeting samples for the voice pickers.

Previews are synthesized through the normal TTS path and cached under the
static audio dir:
  - preview_preset_{Speaker}.wav   — one per preset, shared across all users
  - preview_clone_{profile_id}.wav — one per cloned profile

This replaces the old behaviour of pointing preview_url at the user's raw
uploaded reference clip, which played back their whole original recording
instead of a sample of the cloned voice.
"""
import logging
import os
import uuid as uuid_mod
from typing import Optional

from app.services.tts_engine import tts_service
from app.services.voice_presets import get_preset

logger = logging.getLogger(__name__)

CLONE_GREETING = "Welcome to Aria Appeal."


def preset_preview_filename(speaker: str) -> str:
    return f"preview_preset_{speaker}.wav"


def clone_preview_filename(profile_id) -> str:
    return f"preview_clone_{profile_id}.wav"


def _cache_path(filename: str) -> str:
    return os.path.join(tts_service.output_dir, filename)


def cached_url(filename: str) -> Optional[str]:
    """The served URL if the preview is already on disk, else None."""
    return f"/static/audio/{filename}" if os.path.isfile(_cache_path(filename)) else None


async def _synthesize_into_cache(filename: str, **generate_kwargs) -> Optional[str]:
    """Generate once and move the result to its stable cache name.

    The engine writes to a random uuid filename, so the file is renamed rather
    than regenerated. Returns None if the engine did not actually produce a file.
    """
    existing = cached_url(filename)
    if existing:
        return existing

    try:
        url = await tts_service.generate_audio(**generate_kwargs)
    except Exception:
        logger.exception("Preview synthesis failed for %s", filename)
        return None

    source = os.path.join(tts_service.output_dir, os.path.basename(url or ""))
    if not url or not os.path.isfile(source):
        logger.warning("Preview synthesis produced no file for %s", filename)
        return None

    os.replace(source, _cache_path(filename))
    return f"/static/audio/{filename}"


async def ensure_preset_preview(speaker: str) -> Optional[str]:
    """Preview a preset in ITS OWN language. Raises ValueError for an unknown speaker."""
    preset = get_preset(speaker)
    if preset is None:
        raise ValueError(f"Unknown preset speaker: {speaker}")

    return await _synthesize_into_cache(
        preset_preview_filename(speaker),
        text=preset.greeting,
        voice_profile_id=speaker,
    )


async def ensure_clone_preview(
    profile_id,
    reference_audio_path: Optional[str],
    reference_text: Optional[str],
) -> Optional[str]:
    """Preview a cloned voice by synthesizing the greeting through the clone path."""
    if not reference_audio_path:
        return None

    return await _synthesize_into_cache(
        clone_preview_filename(profile_id),
        text=CLONE_GREETING,
        reference_audio_path=reference_audio_path,
        reference_text=reference_text,
    )


def clone_preview_url(profile_id) -> Optional[str]:
    return cached_url(clone_preview_filename(profile_id))


def delete_clone_preview(profile_id) -> None:
    path = _cache_path(clone_preview_filename(profile_id))
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            logger.warning("Could not delete stale preview %s", path)
```

- [ ] **Step 5: Run it and watch it pass**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest tests/test_voice_preview.py -v
```

Expected: 10 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/voice_preview.py backend/tests/test_voice_preview.py backend/pytest.ini
git commit -m "feat(voice): add cached greeting preview service

Synthesizes a short greeting through the normal TTS path and caches it,
so previews stop replaying the user's raw uploaded reference clip.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 3: Preview endpoints and the corrected `preview_url`

**Files:**

- Modify: `backend/app/schemas/voice_profile.py`
- Modify: `backend/app/api/routes/voice_profiles.py`
- Create: `backend/tests/test_voice_preview_routes.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_voice_preview_routes.py`:

```python
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api import deps
from app.db.session import get_db
from app.models.user import User
from app.models.voice_profile import VoiceProfile


OWNER_ID = uuid.uuid4()
OTHER_ID = uuid.uuid4()
PROFILE_ID = uuid.uuid4()


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalars(self):
        return self

    def first(self):
        return self._value

    def all(self):
        return [self._value] if self._value is not None else []


class _FakeDB:
    def __init__(self, profile):
        self._profile = profile

    async def execute(self, *_a, **_k):
        return _FakeResult(self._profile)

    async def commit(self):
        pass

    async def refresh(self, *_a, **_k):
        pass


def _profile(owner_id=OWNER_ID, ref="/refs/caleb.wav"):
    return VoiceProfile(
        id=PROFILE_ID,
        user_id=owner_id,
        name="Caleb",
        base_model="Qwen3-TTS-12Hz-1.7B-Base",
        reference_audio_path=ref,
        reference_text=None,
    )


def _client(profile, user_id=OWNER_ID):
    user = User(id=user_id, email="u@example.com", hashed_password="x")
    db = _FakeDB(profile)
    app.dependency_overrides[deps.get_current_user] = lambda: user
    app.dependency_overrides[deps.get_db] = lambda: db
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_presets_endpoint_lists_all_nine_with_language_labels():
    client = _client(_profile())

    body = client.get("/api/v1/voice-profiles/presets").json()

    assert len(body) == 9
    aiden = next(p for p in body if p["speaker"] == "Aiden")
    assert aiden["language"] == "en"
    assert aiden["language_label"] == "English"
    anna = next(p for p in body if p["speaker"] == "Ono_Anna")
    assert anna["language"] == "ja"
    assert "ようこそ" in anna["greeting"]
    assert anna["gloss"] == "Welcome to Aria Appeal."


def test_presets_endpoint_does_not_synthesize(monkeypatch):
    from app.services import voice_preview

    async def boom(*_a, **_k):
        raise AssertionError("listing presets must not synthesize")

    monkeypatch.setattr(voice_preview, "ensure_preset_preview", boom)
    client = _client(_profile())

    assert client.get("/api/v1/voice-profiles/presets").status_code == 200


def test_preset_preview_endpoint_returns_the_generated_url(monkeypatch):
    from app.api.routes import voice_profiles as routes

    async def fake(speaker):
        return f"/static/audio/preview_preset_{speaker}.wav"

    monkeypatch.setattr(routes.voice_preview, "ensure_preset_preview", fake)
    client = _client(_profile())

    r = client.post("/api/v1/voice-profiles/presets/Vivian/preview")

    assert r.status_code == 200
    assert r.json()["preview_url"] == "/static/audio/preview_preset_Vivian.wav"


def test_preset_preview_endpoint_404s_for_an_unknown_speaker():
    client = _client(_profile())

    r = client.post("/api/v1/voice-profiles/presets/Nobody/preview")

    assert r.status_code == 404


def test_preset_preview_endpoint_503s_when_synthesis_fails(monkeypatch):
    from app.api.routes import voice_profiles as routes

    async def fake(_speaker):
        return None

    monkeypatch.setattr(routes.voice_preview, "ensure_preset_preview", fake)
    client = _client(_profile())

    assert client.post("/api/v1/voice-profiles/presets/Ryan/preview").status_code == 503


def test_clone_preview_endpoint_returns_the_generated_url(monkeypatch):
    from app.api.routes import voice_profiles as routes

    async def fake(profile_id, reference_audio_path, reference_text):
        assert reference_audio_path == "/refs/caleb.wav"
        return f"/static/audio/preview_clone_{profile_id}.wav"

    monkeypatch.setattr(routes.voice_preview, "ensure_clone_preview", fake)
    client = _client(_profile())

    r = client.post(f"/api/v1/voice-profiles/{PROFILE_ID}/preview")

    assert r.status_code == 200
    assert r.json()["preview_url"] == f"/static/audio/preview_clone_{PROFILE_ID}.wav"


def test_clone_preview_endpoint_404s_for_another_users_profile():
    client = _client(_profile(owner_id=OTHER_ID), user_id=OWNER_ID)

    r = client.post(f"/api/v1/voice-profiles/{PROFILE_ID}/preview")

    assert r.status_code == 404


def test_profile_response_never_exposes_the_raw_upload_path(monkeypatch):
    """The old bug: preview_url was /static/voice_uploads/{file}, i.e. the user's
    entire original recording."""
    from app.schemas.voice_profile import VoiceProfileResponse
    from app.services import voice_preview

    monkeypatch.setattr(voice_preview, "clone_preview_url", lambda _pid: None)

    body = VoiceProfileResponse.from_orm_with_clone_status(_profile())

    assert body.preview_url is None
    assert body.has_cloned_voice is True


def test_profile_response_points_at_the_cached_preview_when_it_exists(monkeypatch):
    from app.schemas.voice_profile import VoiceProfileResponse
    from app.services import voice_preview

    monkeypatch.setattr(
        voice_preview, "clone_preview_url",
        lambda pid: f"/static/audio/preview_clone_{pid}.wav",
    )

    body = VoiceProfileResponse.from_orm_with_clone_status(_profile())

    assert body.preview_url == f"/static/audio/preview_clone_{PROFILE_ID}.wav"
```

- [ ] **Step 2: Run it and watch it fail**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest tests/test_voice_preview_routes.py -v
```

Expected: FAIL — 404/405 on the new routes and the raw-upload assertion.

- [ ] **Step 3: Fix `preview_url` and add the preset schema**

In `backend/app/schemas/voice_profile.py`, replace the whole `from_orm_with_clone_status` classmethod with:

```python
    @classmethod
    def from_orm_with_clone_status(cls, profile):
        # Point at the synthesized greeting cache, NOT the user's raw uploaded
        # reference clip — previewing that played back their whole recording.
        # None until the preview has been generated; the POST route creates it.
        from app.services import voice_preview

        return cls(
            id=profile.id,
            user_id=profile.user_id,
            name=profile.name,
            base_model=profile.base_model,
            has_cloned_voice=profile.reference_audio_path is not None,
            preview_url=voice_preview.clone_preview_url(profile.id),
        )
```

Then append these two schemas to the same file:

```python
class VoicePresetResponse(BaseModel):
    speaker: str
    label: str
    language: str
    language_label: str
    gender: str
    accent: Optional[str] = None
    greeting: str
    gloss: str
    preview_url: Optional[str] = None


class VoicePreviewResponse(BaseModel):
    preview_url: str
```

- [ ] **Step 4: Add the routes**

In `backend/app/api/routes/voice_profiles.py`, extend the schema import and add the service imports:

```python
from app.schemas.voice_profile import (
    VoiceProfileCreate, VoiceProfileResponse, VoiceProfileRename,
    VoiceValidationResponse, VoicePresetResponse, VoicePreviewResponse,
)
from app.services import voice_preview
from app.services.voice_presets import PRESETS, get_preset
```

Add `BackgroundTasks` to the existing `fastapi` import:

```python
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form
```

Add these three routes. **Put the `/presets` routes above the `/{profile_id}` routes**, or FastAPI matches `presets` as a `profile_id` UUID and 422s:

```python
@router.get("/presets", response_model=List[VoicePresetResponse])
async def list_voice_presets():
    """The nine Qwen preset speakers with their native languages.

    Reads the cache only — never synthesizes, so the pickers stay instant.
    """
    return [
        VoicePresetResponse(
            speaker=p.speaker,
            label=p.label,
            language=p.language,
            language_label=p.language_label,
            gender=p.gender,
            accent=p.accent,
            greeting=p.greeting,
            gloss=p.gloss,
            preview_url=voice_preview.cached_url(
                voice_preview.preset_preview_filename(p.speaker)
            ),
        )
        for p in PRESETS
    ]


@router.post("/presets/{speaker}/preview", response_model=VoicePreviewResponse)
async def generate_preset_preview(speaker: str):
    """Synthesize (or return the cached) greeting for a preset, in its own language."""
    if get_preset(speaker) is None:
        raise HTTPException(status_code=404, detail=f"Unknown preset speaker: {speaker}")

    url = await voice_preview.ensure_preset_preview(speaker)
    if not url:
        raise HTTPException(status_code=503, detail="Preview synthesis is unavailable.")
    return VoicePreviewResponse(preview_url=url)


@router.post("/{profile_id}/preview", response_model=VoicePreviewResponse)
async def generate_clone_preview(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Synthesize (or return the cached) greeting in a cloned voice."""
    result = await db.execute(select(VoiceProfile).where(
        VoiceProfile.id == profile_id,
        VoiceProfile.user_id == current_user.id,
    ))
    profile = result.scalars().first()
    if not profile or profile.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Voice profile not found")

    url = await voice_preview.ensure_clone_preview(
        profile.id, profile.reference_audio_path, profile.reference_text
    )
    if not url:
        raise HTTPException(status_code=503, detail="Preview synthesis is unavailable.")
    return VoicePreviewResponse(preview_url=url)
```

- [ ] **Step 5: Generate the clone preview in the background on upload**

So a newly cloned voice usually has its preview ready by the time the list refreshes. In `create_voice_profile`, add `background_tasks: BackgroundTasks,` to the signature (after `file: UploadFile = File(...)`, before the `db` dependency), and add this immediately before the `return`:

```python
    background_tasks.add_task(
        voice_preview.ensure_clone_preview,
        db_voice.id, db_voice.reference_audio_path, db_voice.reference_text,
    )

    return VoiceProfileResponse.from_orm_with_clone_status(db_voice)
```

- [ ] **Step 6: Drop the stale preview when a profile is deleted**

In `delete_voice_profile`, add this line immediately after `await db.commit()`:

```python
    voice_preview.delete_clone_preview(profile_id)
```

- [ ] **Step 7: Run it and watch it pass**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest tests/test_voice_preview_routes.py -v
```

Expected: 9 passed.

- [ ] **Step 8: Run the whole backend suite**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest -q
```

Expected: the same 5 stale failures, everything else passing.

- [ ] **Step 9: Commit**

```bash
git add backend/app/api/routes/voice_profiles.py backend/app/schemas/voice_profile.py backend/tests/test_voice_preview_routes.py
git commit -m "fix(voice): preview the synthesized voice, not the raw upload

preview_url now points at a cached greeting synthesized through the normal
TTS path. Adds preset listing and on-demand preview generation for both
preset and cloned voices.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: Pre-warm the preset previews

The demo must not stall on a first-play synthesis. This script generates all nine ahead of time.

**Files:**

- Create: `backend/scripts/warm_voice_previews.py`

- [ ] **Step 1: Write the script**

Create `backend/scripts/warm_voice_previews.py`:

```python
"""Pre-generate the nine preset voice previews so the pickers never stall.

Run before a demo:
    cd backend && ./.venv/Scripts/python.exe scripts/warm_voice_previews.py

Add --force to regenerate previews that are already cached.
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services import voice_preview  # noqa: E402
from app.services.voice_presets import PRESETS  # noqa: E402


async def main(force: bool) -> int:
    failures = 0
    for preset in PRESETS:
        filename = voice_preview.preset_preview_filename(preset.speaker)
        if force:
            path = os.path.join(voice_preview.tts_service.output_dir, filename)
            if os.path.isfile(path):
                os.remove(path)

        print(f"{preset.speaker:<10} [{preset.language_label}] {preset.greeting}")
        url = await voice_preview.ensure_preset_preview(preset.speaker)
        if url:
            print(f"           -> {url}")
        else:
            print("           -> FAILED")
            failures += 1

    print(f"\n{len(PRESETS) - failures}/{len(PRESETS)} previews ready.")
    return 1 if failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="regenerate cached previews")
    raise SystemExit(asyncio.run(main(parser.parse_args().force)))
```

- [ ] **Step 2: Run it**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe scripts/warm_voice_previews.py
```

Expected: nine lines, each ending in a `/static/audio/preview_preset_*.wav` URL, then `9/9 previews ready.` The first run loads the CustomVoice model onto the GPU, so it takes a minute or two.

- [ ] **Step 3: Listen to all nine**

Play each file under `backend/static/audio/preview_preset_*.wav`. Confirm each non-English voice reads its own language intelligibly, not a mangled attempt at it. If a CJK preview reads badly, the fix is to thread an explicit `language` argument through `TTSService.generate_audio` and `_generate_preset_voice` (both currently hardcode `language="Auto"`) using the catalogue's language name — log it in `Open_Issues.md` rather than expanding this task's scope.

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/warm_voice_previews.py
git commit -m "chore(voice): add preset preview warm-up script

Pre-generates all nine preset greetings so the picker never stalls on a
first-play synthesis during a demo.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5: The frontend preset catalogue

**Files:**

- Create: `frontend/lib/voicePresets.ts`
- Create: `frontend/lib/voicePresets.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/lib/voicePresets.test.ts`:

```typescript
import { VOICE_PRESETS, PRESET_GROUPS, isPresetSpeaker, DEFAULT_PRESET } from './voicePresets'

describe('voicePresets', () => {
    it('lists all nine Qwen preset speakers', () => {
        expect(VOICE_PRESETS).toHaveLength(9)
    })

    it('marks only Aiden and Ryan as English', () => {
        const english = VOICE_PRESETS.filter(p => p.language === 'en').map(p => p.speaker)
        expect(english.sort()).toEqual(['Aiden', 'Ryan'])
    })

    it('puts the English group first', () => {
        expect(PRESET_GROUPS[0].language).toBe('en')
        expect(PRESET_GROUPS[0].label).toBe('English')
    })

    it('groups the remaining languages after English', () => {
        expect(PRESET_GROUPS.map(g => g.language)).toEqual(['en', 'zh', 'ja', 'ko'])
    })

    it('every group is non-empty and every speaker appears exactly once', () => {
        const flat = PRESET_GROUPS.flatMap(g => g.presets.map(p => p.speaker))
        expect(flat).toHaveLength(9)
        expect(new Set(flat).size).toBe(9)
        PRESET_GROUPS.forEach(g => expect(g.presets.length).toBeGreaterThan(0))
    })

    it('captions non-English voices with the English gloss', () => {
        VOICE_PRESETS.filter(p => p.language !== 'en').forEach(p => {
            expect(p.gloss).toBe('Welcome to Aria Appeal.')
        })
    })

    it('defaults to an English preset', () => {
        expect(VOICE_PRESETS.find(p => p.speaker === DEFAULT_PRESET)?.language).toBe('en')
    })

    it('recognises preset speakers and rejects cloned-profile UUIDs', () => {
        expect(isPresetSpeaker('Aiden')).toBe(true)
        expect(isPresetSpeaker('Ono_Anna')).toBe(true)
        expect(isPresetSpeaker('11111111-2222-3333-4444-555555555555')).toBe(false)
        expect(isPresetSpeaker('default')).toBe(false)
    })
})
```

- [ ] **Step 2: Run it and watch it fail**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx jest voicePresets
```

Expected: FAIL — `Cannot find module './voicePresets'`.

- [ ] **Step 3: Implement it**

Create `frontend/lib/voicePresets.ts`:

```typescript
/**
 * Display mirror of backend/app/services/voice_presets.py.
 *
 * Only Aiden and Ryan are native-English Qwen3-TTS presets; the other seven are
 * Chinese, Japanese or Korean. We label rather than hide, and preview each voice
 * in its own language — an English sample from a Chinese speaker is exactly the
 * bad impression the labelling prevents.
 *
 * Scope: this makes the VOICE layer multi-language. Script generation, the studio
 * UI and subtitles remain English-only.
 */

export type PresetLanguage = 'en' | 'zh' | 'ja' | 'ko';

export interface VoicePreset {
    speaker: string;
    label: string;
    language: PresetLanguage;
    languageLabel: string;
    gender: 'male' | 'female';
    accent?: string;
    gloss: string;
}

const GLOSS = 'Welcome to Aria Appeal.';

export const DEFAULT_PRESET = 'Aiden';

export const VOICE_PRESETS: VoicePreset[] = [
    { speaker: 'Aiden', label: 'Aiden — Male', language: 'en', languageLabel: 'English', gender: 'male', gloss: GLOSS },
    { speaker: 'Ryan', label: 'Ryan — Male', language: 'en', languageLabel: 'English', gender: 'male', gloss: GLOSS },
    { speaker: 'Vivian', label: 'Vivian — Female', language: 'zh', languageLabel: 'Chinese', gender: 'female', gloss: GLOSS },
    { speaker: 'Serena', label: 'Serena — Female', language: 'zh', languageLabel: 'Chinese', gender: 'female', gloss: GLOSS },
    { speaker: 'Uncle_Fu', label: 'Uncle Fu — Male', language: 'zh', languageLabel: 'Chinese', gender: 'male', gloss: GLOSS },
    { speaker: 'Dylan', label: 'Dylan — Male, Beijing', language: 'zh', languageLabel: 'Chinese', gender: 'male', accent: 'Beijing', gloss: GLOSS },
    { speaker: 'Eric', label: 'Eric — Male, Sichuan', language: 'zh', languageLabel: 'Chinese', gender: 'male', accent: 'Sichuan', gloss: GLOSS },
    { speaker: 'Ono_Anna', label: 'Ono Anna — Female', language: 'ja', languageLabel: 'Japanese', gender: 'female', gloss: GLOSS },
    { speaker: 'Sohee', label: 'Sohee — Female', language: 'ko', languageLabel: 'Korean', gender: 'female', gloss: GLOSS },
];

// English first — it is the only language the rest of the product speaks.
const LANGUAGE_ORDER: PresetLanguage[] = ['en', 'zh', 'ja', 'ko'];

export interface PresetGroup {
    language: PresetLanguage;
    label: string;
    presets: VoicePreset[];
}

export const PRESET_GROUPS: PresetGroup[] = LANGUAGE_ORDER.map(language => ({
    language,
    label: VOICE_PRESETS.find(p => p.language === language)!.languageLabel,
    presets: VOICE_PRESETS.filter(p => p.language === language),
}));

const SPEAKERS = new Set(VOICE_PRESETS.map(p => p.speaker));

export function isPresetSpeaker(value: string): boolean {
    return SPEAKERS.has(value);
}

export function getPreset(speaker: string): VoicePreset | undefined {
    return VOICE_PRESETS.find(p => p.speaker === speaker);
}
```

- [ ] **Step 4: Run it and watch it pass**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx jest voicePresets
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/voicePresets.ts frontend/lib/voicePresets.test.ts
git commit -m "feat(voice): add grouped multi-language preset catalogue

English first, Aiden/Ryan as defaults, the other seven labelled by their
native language rather than hidden.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 6: The shared preview button

**Files:**

- Create: `frontend/components/ui/VoicePreviewButton.tsx`

- [ ] **Step 1: Implement it**

Create `frontend/components/ui/VoicePreviewButton.tsx`:

```tsx
'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Loader2, Play, Square } from 'lucide-react';
import { useSession } from 'next-auth/react';
import { API_URL } from '@/lib/config';
import { apiFetch } from '@/lib/api';

interface VoicePreviewButtonProps {
    /** A preset speaker name, or a cloned profile UUID. */
    target: string;
    kind: 'preset' | 'clone';
    /** Already-cached preview URL, if the caller knows one. */
    previewUrl?: string | null;
    /** Caption shown while playing — the English gloss for a non-English voice. */
    caption?: string;
    className?: string;
}

function absolute(url: string): string {
    return url.startsWith('http') ? url : `${API_URL.replace(/\/api\/v1$/, '')}${url}`;
}

export const VoicePreviewButton: React.FC<VoicePreviewButtonProps> = ({
    target, kind, previewUrl, caption, className,
}) => {
    const { data: session } = useSession();
    const [isLoading, setIsLoading] = useState(false);
    const [isPlaying, setIsPlaying] = useState(false);
    const [url, setUrl] = useState<string | null>(previewUrl ?? null);
    const audioRef = useRef<HTMLAudioElement | null>(null);

    useEffect(() => {
        setUrl(previewUrl ?? null);
    }, [previewUrl, target]);

    const stop = () => {
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current = null;
        }
        setIsPlaying(false);
    };

    // Mirrors the studio's teardown rule: unmounting must stop playback.
    useEffect(() => stop, []);

    const play = (src: string) => {
        stop();
        const audio = new Audio(absolute(src));
        audio.onended = () => setIsPlaying(false);
        audio.onerror = () => setIsPlaying(false);
        audio.play().catch(() => setIsPlaying(false));
        audioRef.current = audio;
        setIsPlaying(true);
    };

    const handleClick = async (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();

        if (isPlaying) {
            stop();
            return;
        }
        if (url) {
            play(url);
            return;
        }

        setIsLoading(true);
        try {
            const path = kind === 'preset'
                ? `/voice-profiles/presets/${target}/preview`
                : `/voice-profiles/${target}/preview`;
            const res = await apiFetch(path, { method: 'POST', token: session?.accessToken });
            if (!res.ok) return;
            const data = await res.json();
            if (data.preview_url) {
                setUrl(data.preview_url);
                play(data.preview_url);
            }
        } catch {
            /* leave the button idle; the user can retry */
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <span className={`inline-flex items-center gap-1.5 ${className ?? ''}`}>
            <button
                type="button"
                onClick={handleClick}
                aria-label={isPlaying ? `Stop preview of ${target}` : `Preview ${target}`}
                disabled={isLoading}
                className={`h-8 w-8 rounded-full flex items-center justify-center transition-colors flex-shrink-0 ${
                    isPlaying
                        ? 'text-moore-red bg-moore-red/10'
                        : 'text-moore-mid-gray hover:text-moore-red hover:bg-moore-red/10'
                } disabled:opacity-50`}
            >
                {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    : isPlaying ? <Square className="w-3.5 h-3.5" />
                    : <Play className="w-3.5 h-3.5" />}
            </button>
            {isPlaying && caption && (
                <span className="text-[10px] text-moore-mid-gray italic truncate">“{caption}”</span>
            )}
        </span>
    );
};

export default VoicePreviewButton;
```

- [ ] **Step 2: Typecheck**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/ui/VoicePreviewButton.tsx
git commit -m "feat(voice): add shared lazy voice preview button

Requests the preview on first play, caches the URL, and stops playback on
unmount.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 7: `VoiceList` — a preview for every profile

**Files:**

- Modify: `frontend/components/dashboard/VoiceList.tsx`

- [ ] **Step 1: Replace the hand-rolled player with the shared button**

Add the import:

```typescript
import VoicePreviewButton from '@/components/ui/VoicePreviewButton';
```

Then replace this block (currently around line 190, the play button gated on `has_cloned_voice && preview_url`):

```tsx
                                    {profile.has_cloned_voice && profile.preview_url && (
                                        <button
                                            onClick={() => togglePlayback(profile)}
                                            className={`h-8 w-8 rounded-full flex items-center justify-center transition-colors ${
                                                playingId === profile.id
                                                    ? 'text-moore-red bg-moore-red/10'
                                                    : 'text-moore-mid-gray hover:text-moore-red hover:bg-moore-red/10'
                                            }`}
                                        >
                                            {playingId === profile.id ? (
                                                <Square className="w-3.5 h-3.5" />
                                            ) : (
                                                <Play className="w-3.5 h-3.5" />
                                            )}
                                        </button>
                                    )}
```

with:

```tsx
                                    {profile.has_cloned_voice && (
                                        <VoicePreviewButton
                                            target={profile.id}
                                            kind="clone"
                                            previewUrl={profile.preview_url}
                                            caption="Welcome to Aria Appeal."
                                        />
                                    )}
```

The button no longer requires `preview_url` to be present — it generates one on first click, which is the whole point of the fix.

- [ ] **Step 2: Delete the now-dead local playback code**

Remove `playingId`, `audioRef`, `togglePlayback`, `stopPlayback`, and the `useEffect(() => { return () => stopPlayback(); }, [])` cleanup. In `deleteProfile`, remove the `if (playingId === id) stopPlayback();` line. Drop `Play` and `Square` from the `lucide-react` import if nothing else in the file uses them.

- [ ] **Step 3: Typecheck and lint**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx tsc --noEmit && npm run lint
```

Expected: no type errors, no new lint errors about unused variables.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/dashboard/VoiceList.tsx
git commit -m "fix(voice): show a preview button for every cloned profile

The button no longer requires a pre-existing preview_url; it generates one
on first click.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 8: Language-grouped picker in the studio inspector

**Files:**

- Modify: `frontend/components/studio/InspectorPanel.tsx`

- [ ] **Step 1: Replace the local preset list with the shared catalogue**

Delete the `PRESET_SPEAKERS` constant and its comment at the top of the file (lines ~21-27) and import the catalogue instead:

```typescript
import { PRESET_GROUPS, isPresetSpeaker, getPreset } from '@/lib/voicePresets';
import VoicePreviewButton from '@/components/ui/VoicePreviewButton';
```

- [ ] **Step 2: Fix the two `PRESET_SPEAKERS.some(...)` call sites**

In `handleVoiceChange`, change:

```typescript
        const isPreset = PRESET_SPEAKERS.some(p => p.value === val);
```

to:

```typescript
        const isPreset = isPresetSpeaker(val);
```

and make the identical change inside the Global Voice `onValueChange` handler further down the file.

- [ ] **Step 3: Group the select content by language**

Replace the whole `VoiceSelectContent` function with:

```tsx
function VoiceSelectContent({ tab, voiceProfiles }: { tab: 'preset' | 'cloned'; voiceProfiles: VoiceProfile[] }) {
    return (
        <SelectContent>
            {tab === 'preset' && <SelectItem value="default">Default / Auto (Aiden)</SelectItem>}
            {tab === 'preset' && PRESET_GROUPS.map(group => (
                <React.Fragment key={group.language}>
                    <div className="px-2 pt-2 pb-1 text-[10px] font-medium uppercase tracking-wider text-moore-mid-gray">
                        {group.label}
                    </div>
                    {group.presets.map(p => (
                        <SelectItem key={p.speaker} value={p.speaker}>{p.label}</SelectItem>
                    ))}
                </React.Fragment>
            ))}
            {tab === 'cloned' && voiceProfiles.map(vp => (
                <SelectItem key={vp.id} value={vp.id}>{vp.name}</SelectItem>
            ))}
            {tab === 'cloned' && voiceProfiles.length === 0 && (
                <div className="px-3 py-4 text-center text-xs text-moore-mid-gray italic">
                    No cloned voices yet.<br />Upload one from the dashboard.
                </div>
            )}
        </SelectContent>
    );
}
```

- [ ] **Step 4: Add a preview button beside the segment Voice select**

In the segment inspector's Voice block, wrap the `<Select>` so it reads:

```tsx
            <div className="space-y-1.5">
                <label className="text-sm font-medium text-moore-dark-gray">Voice</label>
                <VoiceTabToggle tab={voiceTab} onChange={setVoiceTab} />
                <div className="flex items-center gap-1.5">
                    <div className="flex-1 min-w-0">
                        <Select
                            value={voiceTab === 'preset'
                                ? (activeSegment.speaker_preset || 'default')
                                : (activeSegment.voice_profile_id || 'default')
                            }
                            onValueChange={handleVoiceChange}
                        >
                            <SelectTrigger className="rounded-xl border-gray-200 focus:ring-moore-red/30">
                                <SelectValue placeholder="Select a voice..." />
                            </SelectTrigger>
                            <VoiceSelectContent tab={voiceTab} voiceProfiles={voiceProfiles} />
                        </Select>
                    </div>
                    {voiceTab === 'preset' && activeSegment.speaker_preset && (
                        <VoicePreviewButton
                            target={activeSegment.speaker_preset}
                            kind="preset"
                            caption={getPreset(activeSegment.speaker_preset)?.gloss}
                        />
                    )}
                    {voiceTab === 'cloned' && activeSegment.voice_profile_id && (
                        <VoicePreviewButton
                            target={activeSegment.voice_profile_id}
                            kind="clone"
                            previewUrl={voiceProfiles.find(v => v.id === activeSegment.voice_profile_id)?.preview_url}
                            caption="Welcome to Aria Appeal."
                        />
                    )}
                </div>
                {voiceTab === 'preset' && activeSegment.speaker_preset
                    && getPreset(activeSegment.speaker_preset)?.language !== 'en' && (
                    <p className="text-[10px] text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-2 py-1">
                        {getPreset(activeSegment.speaker_preset)?.languageLabel} narration — this voice
                        is not native to English. Scripts and captions stay English.
                    </p>
                )}
            </div>
```

That warning is the honest half of the multi-language framing: the voice layer covers four languages, the rest of the product does not.

- [ ] **Step 5: Typecheck and lint**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx tsc --noEmit && npm run lint
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/studio/InspectorPanel.tsx
git commit -m "feat(voice): language-grouped preset picker in the studio inspector

English first, the other seven grouped by native language with an inline
preview and a note that scripts and captions stay English.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 9: Language-grouped picker in campaign creation

**Files:**

- Modify: `frontend/components/dashboard/create-campaign-modal.tsx`

- [ ] **Step 1: Replace the local preset list**

Delete the `PRESET_SPEAKERS` constant and its comment (lines ~30-36) and import instead:

```typescript
import { PRESET_GROUPS, isPresetSpeaker, getPreset } from '@/lib/voicePresets';
import VoicePreviewButton from '@/components/ui/VoicePreviewButton';
```

- [ ] **Step 2: Fix the payload branch**

Change:

```typescript
                if (PRESET_SPEAKERS.some(p => p.value === selectedVoice)) {
```

to:

```typescript
                if (isPresetSpeaker(selectedVoice)) {
```

- [ ] **Step 3: Group the select and add the preview**

Replace the Voice block's `<Select>` and its trailing helper paragraph with:

```tsx
                    <div className="flex items-center gap-1.5">
                        <div className="flex-1 min-w-0">
                            <Select value={selectedVoice} onValueChange={setSelectedVoice}>
                                <SelectTrigger className="rounded-xl border-gray-200 focus:ring-2 focus:ring-moore-red/30">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="default">Default / Auto (Aiden)</SelectItem>
                                    {PRESET_GROUPS.map(group => (
                                        <React.Fragment key={group.language}>
                                            <div className="px-2 pt-2 pb-1 text-[10px] font-medium uppercase tracking-wider text-moore-mid-gray">
                                                {group.label}
                                            </div>
                                            {group.presets.map(p => (
                                                <SelectItem key={p.speaker} value={p.speaker}>{p.label}</SelectItem>
                                            ))}
                                        </React.Fragment>
                                    ))}
                                    {voiceProfiles.length > 0 && (
                                        <div className="px-2 pt-2 pb-1 text-[10px] font-medium uppercase tracking-wider text-moore-mid-gray">
                                            Cloned voices
                                        </div>
                                    )}
                                    {voiceProfiles.map(vp => (
                                        <SelectItem key={vp.id} value={vp.id}>{vp.name} (cloned)</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        {isPresetSpeaker(selectedVoice) && (
                            <VoicePreviewButton
                                target={selectedVoice}
                                kind="preset"
                                caption={getPreset(selectedVoice)?.gloss}
                            />
                        )}
                        {selectedVoice !== 'default' && !isPresetSpeaker(selectedVoice) && (
                            <VoicePreviewButton
                                target={selectedVoice}
                                kind="clone"
                                previewUrl={voiceProfiles.find(v => v.id === selectedVoice)?.preview_url}
                                caption="Welcome to Aria Appeal."
                            />
                        )}
                    </div>
                    <p className="text-[11px] text-moore-mid-gray">
                        Applied to every segment. Narration covers English, Chinese, Japanese and
                        Korean; scripts and captions are English only.
                    </p>
```

- [ ] **Step 4: Typecheck, lint, build**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx tsc --noEmit && npm run lint && npm run build
```

Expected: all three succeed.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/dashboard/create-campaign-modal.tsx
git commit -m "feat(voice): language-grouped preset picker in campaign creation

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 10: Full verification

- [ ] **Step 1: Backend suite**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest -q
```

Expected: the same 5 stale failures as the baseline and nothing else red. A sixth failure means something in this plan broke.

- [ ] **Step 2: Frontend suite**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx jest
```

Expected: the pre-existing 6 failures plus 8 new passes in `voicePresets.test.ts`.

- [ ] **Step 3: Production build**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npm run build
```

Expected: success.

- [ ] **Step 4: Manual — cloned voice preview**

Start both servers:

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/Activate.ps1; uvicorn app.main:app --reload
```

```bash
cd "D:/Repo/Aria Appeal/frontend" && npm run dev
```

On the dashboard, press play on a cloned voice profile. Confirm it says **"Welcome to Aria Appeal."** in the cloned voice — not the user's original uploaded recording. Press play again: it must be instant (served from the cache).

- [ ] **Step 5: Manual — preset previews in their own languages**

Open a campaign in the studio, select a segment, and switch the voice tab to the preset list. Confirm:

- The list is grouped `English / Chinese / Japanese / Korean`, English first, with Aiden and Ryan at the top.
- Selecting a non-English voice shows the amber "narration only" note.
- Pressing play on Vivian plays Chinese; Ono Anna plays Japanese; Sohee plays Korean; Aiden and Ryan play English.
- While a non-English preview plays, the English gloss appears as caption text next to the button.

- [ ] **Step 6: Manual — campaign creation picker**

Open the create-campaign modal. Confirm the same grouping and the preview button beside the select, and that the helper text names the scope honestly.

- [ ] **Step 7: Confirm no raw upload is ever served as a preview**

```bash
cd "D:/Repo/Aria Appeal" && grep -rn "voice_uploads" backend/app/schemas/ frontend/components/
```

Expected: no matches. If `preview_url` still builds a `/static/voice_uploads/` path anywhere, the original bug is still live.

- [ ] **Step 8: Push**

```bash
git status
git push origin feat/video-previs
```

---

## What this deliberately does NOT do

- No i18n framework, no translated UI chrome, no localised script generation, no non-English subtitles. Say **"multi-language narration"** in the room, not "multi-language product" — the gap is easy to probe and cheap to be straight about.
- No preview for the `default` / auto option; it resolves to Aiden, whose own preview covers it.
- No per-user preset previews. Preset audio is identical for everyone, so the cache is shared.
