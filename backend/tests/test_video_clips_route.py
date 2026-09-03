import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api import deps
from app.models.user import User
from app.models.project import Project
from app.models.video_clip import VideoClip, VideoClipStatus, VideoSourceType


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
