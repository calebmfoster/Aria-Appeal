import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api import deps
from app.models.user import User
from app.models.project import Project
from app.models.video_clip import VideoClip, VideoClipStatus, VideoSourceType
from app.models.script_segment import ScriptSegment


OWNER_ID = uuid.uuid4()
OTHER_ID = uuid.uuid4()
PROJECT_ID = uuid.uuid4()


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalars(self):
        return self

    def first(self):
        return self._value


class _FakeDB:
    def __init__(self, project):
        self._project = project

    async def execute(self, *_a, **_k):
        return _FakeResult(self._project)

    async def commit(self):
        pass


def _clip(order, status=VideoClipStatus.READY, **kw):
    return VideoClip(
        id=uuid.uuid4(),
        project_id=PROJECT_ID,
        sequence_order=order,
        source_type=VideoSourceType.ASSET,
        status=status,
        prompt=f"shot {order}",
        video_url=f"/static/video/assets/c{order}.mp4",
        duration_ms=2000,
        **kw,
    )


def _project(owner_id=OWNER_ID, clips=None, brief=None, subs=None):
    p = Project(
        id=PROJECT_ID,
        user_id=owner_id,
        title="T",
        target_audience={"medium": "video"},
        video_brief=brief,
        subtitle_style=subs,
    )
    p.video_clips = clips if clips is not None else []
    p.segments = []
    return p


def _client(project, user_id=OWNER_ID):
    user = User(id=user_id, email="u@example.com", hashed_password="x")
    app.dependency_overrides[deps.get_current_user] = lambda: user
    app.dependency_overrides[deps.get_db] = lambda: _FakeDB(project)
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_clips_are_returned_in_sequence_order():
    project = _project(clips=[_clip(2), _clip(0), _clip(1)])
    client = _client(project)

    r = client.get(f"/api/v1/projects/{PROJECT_ID}/video/clips")

    assert r.status_code == 200
    assert [c["sequence_order"] for c in r.json()["clips"]] == [0, 1, 2]


def test_clips_response_carries_brief_and_subtitle_style():
    brief = {"style_prompt": "warm 16mm", "character_sheet": "MAYA, age 8"}
    subs = {"enabled": True, "font_size": 54, "position": "bottom", "color": "FFFFFF"}
    client = _client(_project(clips=[_clip(0)], brief=brief, subs=subs))

    body = client.get(f"/api/v1/projects/{PROJECT_ID}/video/clips").json()

    assert body["video_brief"]["style_prompt"] == "warm 16mm"
    assert body["subtitle_style"]["font_size"] == 54


def test_clips_response_tolerates_null_brief_and_style():
    client = _client(_project(clips=[_clip(0)]))

    body = client.get(f"/api/v1/projects/{PROJECT_ID}/video/clips").json()

    assert body["video_brief"] is None
    assert body["subtitle_style"] is None


def test_clips_exposes_timeline_positions_and_prompt():
    client = _client(_project(clips=[
        _clip(0, timeline_start_ms=0, timeline_end_ms=4000),
    ]))

    clip = client.get(f"/api/v1/projects/{PROJECT_ID}/video/clips").json()["clips"][0]

    assert clip["timeline_start_ms"] == 0
    assert clip["timeline_end_ms"] == 4000
    assert clip["prompt"] == "shot 0"


def test_clips_returns_empty_list_when_project_has_none():
    client = _client(_project(clips=[]))

    assert client.get(f"/api/v1/projects/{PROJECT_ID}/video/clips").json()["clips"] == []


def test_clips_404s_for_another_users_project():
    client = _client(_project(owner_id=OTHER_ID), user_id=OWNER_ID)

    r = client.get(f"/api/v1/projects/{PROJECT_ID}/video/clips")

    assert r.status_code == 404


class _Seg:
    """Plain stand-in for the pure fingerprint tests."""
    def __init__(self, sid, order, text, audio_url):
        self.id = sid
        self.sequence_order = order
        self.text = text
        self.audio_url = audio_url


def _orm_seg(text, audio_url, order=0):
    """Route tests need real ORM instances — assigning plain objects to the
    segments relationship trips SQLAlchemy's instrumentation."""
    return ScriptSegment(
        id=uuid.uuid4(),
        project_id=PROJECT_ID,
        sequence_order=order,
        text=text,
        audio_url=audio_url,
    )


def test_fingerprint_changes_when_a_segment_is_regenerated():
    """Regenerating gives the segment a fresh audio_url, which must mark the
    already-built animatic stale."""
    from app.services.video.assembly import source_fingerprint

    before = [_Seg("a", 0, "line one", "/static/audio/old.wav")]
    after = [_Seg("a", 0, "line one", "/static/audio/new.wav")]

    assert source_fingerprint(before) != source_fingerprint(after)


def test_fingerprint_changes_when_text_is_edited():
    from app.services.video.assembly import source_fingerprint

    before = [_Seg("a", 0, "To be an astronaut.", "/static/audio/x.wav")]
    after = [_Seg("a", 0, "To explore the stars.", "/static/audio/x.wav")]

    assert source_fingerprint(before) != source_fingerprint(after)


def test_fingerprint_changes_with_subtitle_style():
    from app.services.video.assembly import source_fingerprint

    segs = [_Seg("a", 0, "line", "/static/audio/x.wav")]

    assert source_fingerprint(segs, {"font_size": 54}) != source_fingerprint(segs, {"font_size": 48})


def test_fingerprint_is_stable_for_unchanged_input_and_order_independent():
    from app.services.video.assembly import source_fingerprint

    a = _Seg("a", 0, "one", "/static/audio/1.wav")
    b = _Seg("b", 1, "two", "/static/audio/2.wav")

    assert source_fingerprint([a, b]) == source_fingerprint([b, a])


def test_export_status_reports_stale_when_the_script_moved_on():
    project = _project(clips=[_clip(0)], brief={
        "video_export_status": "ready",
        "video_master_url": "/static/video/a.mp4",
        "video_source_fingerprint": "stale-value-from-an-older-assembly",
    })
    project.segments = [_orm_seg("edited line", "/static/audio/new.wav")]
    client = _client(project)

    body = client.get(f"/api/v1/projects/{PROJECT_ID}/video/export").json()

    assert body["status"] == "ready"
    assert body["stale"] is True


def test_export_status_is_not_stale_right_after_assembly():
    from app.services.video.assembly import source_fingerprint

    segs = [_orm_seg("line", "/static/audio/new.wav")]
    project = _project(clips=[_clip(0)], brief={
        "video_export_status": "ready",
        "video_master_url": "/static/video/a.mp4",
        "video_source_fingerprint": source_fingerprint(segs, None),
    })
    project.segments = segs
    client = _client(project)

    assert client.get(f"/api/v1/projects/{PROJECT_ID}/video/export").json()["stale"] is False


def test_export_status_is_not_stale_before_any_assembly():
    """No animatic yet means nothing to be out of date."""
    project = _project(clips=[_clip(0)])
    project.segments = [_orm_seg("line", "/static/audio/new.wav")]
    client = _client(project)

    assert client.get(f"/api/v1/projects/{PROJECT_ID}/video/export").json()["stale"] is False
