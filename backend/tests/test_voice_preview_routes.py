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
    from app.api.routes import voice_profiles as routes

    async def boom(*_a, **_k):
        raise AssertionError("listing presets must not synthesize")

    monkeypatch.setattr(routes.voice_preview, "ensure_preset_preview", boom)
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
