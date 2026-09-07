import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api import deps
from app.models.user import User
from app.models.project import Project, ProjectStatus


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
        self.commits = 0

    async def execute(self, *_a, **_k):
        return _FakeResult(self._project)

    async def commit(self):
        self.commits += 1

    async def refresh(self, *_a, **_k):
        pass


def _project(owner_id=OWNER_ID, audience=None, subs=None):
    p = Project(
        id=PROJECT_ID,
        user_id=owner_id,
        title="T",
        target_audience=audience if audience is not None else {"audience": "donors"},
        status=ProjectStatus.GENERATED,
        subtitle_style=subs,
    )
    p.segments = []
    p.video_clips = []
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


def test_patch_sets_medium_without_clobbering_other_audience_keys():
    project = _project(audience={"audience": "donors", "emotion": "hope"})
    client, db = _client(project)

    r = client.patch(f"/api/v1/projects/{PROJECT_ID}", json={"medium": "video"})

    assert r.status_code == 200
    assert project.target_audience["medium"] == "video"
    assert project.target_audience["emotion"] == "hope"
    assert db.commits == 1


def test_patch_reassigns_target_audience_rather_than_mutating_in_place():
    """target_audience is a JSON column — mutating the dict in place does not
    mark the attribute dirty and the write is silently dropped."""
    project = _project(audience={"audience": "donors"})
    before = project.target_audience
    client, _ = _client(project)

    client.patch(f"/api/v1/projects/{PROJECT_ID}", json={"medium": "video"})

    assert project.target_audience is not before


def test_patch_sets_subtitle_style():
    project = _project()
    client, _ = _client(project)

    r = client.patch(
        f"/api/v1/projects/{PROJECT_ID}",
        json={"subtitle_style": {"enabled": False, "font_size": 42,
                                 "position": "bottom", "color": "FFFFFF"}},
    )

    assert r.status_code == 200
    assert project.subtitle_style["enabled"] is False
    assert project.subtitle_style["font_size"] == 42


def test_patch_rejects_an_unknown_medium():
    client, _ = _client(_project())

    r = client.patch(f"/api/v1/projects/{PROJECT_ID}", json={"medium": "hologram"})

    assert r.status_code == 422


def test_patch_with_empty_body_changes_nothing():
    project = _project(audience={"audience": "donors"})
    client, _ = _client(project)

    r = client.patch(f"/api/v1/projects/{PROJECT_ID}", json={})

    assert r.status_code == 200
    assert "medium" not in project.target_audience


def test_patch_404s_for_another_users_project():
    client, _ = _client(_project(owner_id=OTHER_ID), user_id=OWNER_ID)

    r = client.patch(f"/api/v1/projects/{PROJECT_ID}", json={"medium": "video"})

    assert r.status_code == 404
