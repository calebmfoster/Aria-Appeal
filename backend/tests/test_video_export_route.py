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
    """Returns a preset project for any select; records commits."""

    def __init__(self, project):
        self._project = project
        self.commits = 0

    async def execute(self, *_a, **_k):
        return _FakeResult(self._project)

    async def commit(self):
        self.commits += 1


def _clip(order, status=VideoClipStatus.READY):
    return VideoClip(
        id=uuid.uuid4(),
        project_id=PROJECT_ID,
        sequence_order=order,
        source_type=VideoSourceType.ASSET,
        status=status,
        video_url=f"/static/video/assets/c{order}.mp4",
        duration_ms=2000,
    )


def _project(owner_id=OWNER_ID, clips=None, brief=None):
    p = Project(
        id=PROJECT_ID,
        user_id=owner_id,
        title="T",
        target_audience={},
        video_brief=brief,
    )
    p.video_clips = clips if clips is not None else [_clip(0), _clip(1)]
    p.segments = []
    return p


def _client(project, user_id=OWNER_ID):
    user = User(id=user_id, email="u@example.com", hashed_password="x")
    db = _FakeDB(project)
    app.dependency_overrides[deps.get_current_user] = lambda: user
    app.dependency_overrides[deps.get_db] = lambda: db
    return TestClient(app), db


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_export_starts_and_reports_running(monkeypatch):
    from app.api.routes import video as video_routes
    started = {}

    def fake_schedule(background_tasks, project_id):
        started["id"] = project_id

    monkeypatch.setattr(video_routes, "_schedule_assembly", fake_schedule)

    client, db = _client(_project())
    r = client.post(f"/api/v1/projects/{PROJECT_ID}/video/export")
    assert r.status_code == 200
    assert r.json()["status"] == "running"
    assert started["id"] == PROJECT_ID


def test_export_rejects_when_clips_not_ready(monkeypatch):
    from app.api.routes import video as video_routes
    monkeypatch.setattr(video_routes, "_schedule_assembly", lambda bt, pid: None)

    project = _project(clips=[_clip(0), _clip(1, status=VideoClipStatus.PENDING)])
    client, _ = _client(project)
    r = client.post(f"/api/v1/projects/{PROJECT_ID}/video/export")
    assert r.status_code == 400
    assert "not ready" in r.json()["detail"].lower()


def test_export_rejects_when_no_clips(monkeypatch):
    from app.api.routes import video as video_routes
    monkeypatch.setattr(video_routes, "_schedule_assembly", lambda bt, pid: None)

    client, _ = _client(_project(clips=[]))
    r = client.post(f"/api/v1/projects/{PROJECT_ID}/video/export")
    assert r.status_code == 400


def test_export_404s_for_another_users_project(monkeypatch):
    from app.api.routes import video as video_routes
    monkeypatch.setattr(video_routes, "_schedule_assembly", lambda bt, pid: None)

    client, _ = _client(_project(owner_id=OTHER_ID), user_id=OWNER_ID)
    r = client.post(f"/api/v1/projects/{PROJECT_ID}/video/export")
    assert r.status_code == 404


def test_status_reports_idle_before_any_export():
    client, _ = _client(_project())
    r = client.get(f"/api/v1/projects/{PROJECT_ID}/video/export")
    assert r.status_code == 200
    assert r.json()["status"] == "idle"
    assert r.json()["video_master_url"] is None


def test_status_reports_ready_with_url():
    brief = {"video_export_status": "ready", "video_master_url": "/static/video/a.mp4"}
    client, _ = _client(_project(brief=brief))
    r = client.get(f"/api/v1/projects/{PROJECT_ID}/video/export")
    body = r.json()
    assert body["status"] == "ready"
    assert body["video_master_url"] == "/static/video/a.mp4"


def test_status_surfaces_failure_reason():
    brief = {"video_export_status": "failed", "video_export_error": "ffmpeg exploded"}
    client, _ = _client(_project(brief=brief))
    body = client.get(f"/api/v1/projects/{PROJECT_ID}/video/export").json()
    assert body["status"] == "failed"
    assert "ffmpeg exploded" in body["error"]


def test_status_404s_for_another_users_project():
    client, _ = _client(_project(owner_id=OTHER_ID), user_id=OWNER_ID)
    r = client.get(f"/api/v1/projects/{PROJECT_ID}/video/export")
    assert r.status_code == 404
