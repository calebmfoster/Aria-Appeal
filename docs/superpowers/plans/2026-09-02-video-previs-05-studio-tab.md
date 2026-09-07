# Plan 5 — Audio | Video Studio Tab — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give a video-medium campaign an `Audio | Video` toggle in the studio that previews the assembled animatic and can trigger assembly, while leaving audio-only campaigns byte-for-byte identical to today.

**Architecture:** The Video tab reuses the studio's existing 30/45/25 three-column shell and swaps what sits in each column — segment list with poster frames on the left, the assembled `<video>` plus a clip strip in the centre, a read-only clip inspector on the right. Campaign medium lives at `target_audience.medium` (absent means `"audio"`, so no migration and no behaviour change for existing campaigns). One new read endpoint (`GET /projects/{id}/video/clips`) plus a project `PATCH` for persisting `medium` and `subtitle_style`. Export reuses the existing `POST/GET /projects/{id}/video/export` and polls it.

**Tech Stack:** FastAPI + SQLAlchemy (async) + Pydantic on the backend; Next.js 15 App Router, React 19, Zustand, Tailwind, Jest + React Testing Library on the frontend.

---

## Scope

**In:** medium flag, tab toggle, clip list, animatic preview, clip strip, read-only clip inspector, subtitle toggle + font size (applies on next assembly), assemble/poll/export, playback teardown.

**Out (needs Plan 3, which is written but not executed):** reorder, trim, replace, per-clip regenerate, editable shot prompts. Do not build toward them.

---

## Baseline you must know before starting

Run these once and write the numbers down. They are the "unchanged" bar.

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest -q
```

Expected: `5 failed, 81 passed`. Those 5 are stale Celery-era / pre-refactor tests documented in `documentation/Open_Issues.md`. **Do not fix them, do not chase them.** If you ever see 6 failures, you broke something.

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx jest
```

Expected: `Test Suites: 2 failed, 1 passed`, `Tests: 6 failed, 1 passed`. `InspectorPanel.test.tsx` and `ScriptEditor.test.tsx` are stale — they mock the Zustand store but not `next-auth/react` or `next/navigation`, which those components now call. **Do not fix them either.** Every new test file you write in this plan MUST avoid that trap: either mock those modules or keep the component under test free of them.

Other environment facts:

- Bare `python` is NOT on PATH. Always `backend/.venv/Scripts/python.exe`.
- `ffmpeg`/`ffprobe` 8.1.2 are installed and on PATH.
- Supabase is shared and live. The demo campaign is `Make-A-Wish (Demo)` on `admin@example.com`.
- `frontend/package.json` has no `test` script; run Jest with `npx jest`.
- Rebuild the demo animatic any time with:

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe scripts/assemble_demo.py
```

---

## File Structure

**Backend — create:**

- `backend/tests/test_video_clips_route.py` — tests for the new clips endpoint.
- `backend/tests/test_project_settings_route.py` — tests for the project PATCH.

**Backend — modify:**

- `backend/app/services/video/assembly.py` — add `Beat.clip_id`; persist timeline positions in `assemble_project`.
- `backend/app/api/routes/video.py` — add `GET /{project_id}/video/clips`.
- `backend/app/api/routes/projects.py` — add `PATCH /{project_id}`; accept `medium` in create.
- `backend/app/schemas/video.py` — add `VideoClipsResponse`.
- `backend/app/schemas/project.py` — add `medium` to `ProjectCreate`; add `ProjectSettingsUpdate`.
- `backend/tests/test_assembly_timeline.py` — assert timeline write-back.
- `backend/scripts/seed_makeawish_demo.py` — seed the demo as a video campaign.

**Frontend — create:**

- `frontend/types/video.ts` — `VideoClip`, `VideoBrief`, `SubtitleStyle`, `VideoExportState`, `CampaignMedium`.
- `frontend/hooks/useVideoExport.ts` — the assemble/poll state machine, isolated so it is testable without a DOM player.
- `frontend/hooks/useVideoExport.test.ts` — its tests.
- `frontend/components/studio/StudioTabs.tsx` — the `Audio | Video` toggle. Renders `null` for audio-only.
- `frontend/components/studio/StudioTabs.test.tsx`
- `frontend/components/studio/VideoSegmentList.tsx` — left column for the Video tab.
- `frontend/components/studio/VideoPreview.tsx` — centre column: player + clip strip.
- `frontend/components/studio/VideoPreview.test.tsx`
- `frontend/components/studio/VideoInspector.tsx` — right column for the Video tab.

**Frontend — modify:**

- `frontend/types/studio.ts` — re-export video types so imports stay in one place.
- `frontend/store/studioStore.ts` — add the video slice.
- `frontend/app/dashboard/studio/[id]/page.tsx` — tab bar, contextual export button, conditional columns.
- `frontend/components/dashboard/create-campaign-modal.tsx` — medium toggle.
- `frontend/components/dashboard/CampaignList.tsx` — medium badge.

---

## Task 1: Persist timeline positions during assembly

`VideoClip.timeline_start_ms` / `timeline_end_ms` exist as columns but nothing ever writes them — `compute_timeline` returns `Beat`s and throws the clip mapping away. The clip strip needs those numbers to seek. This task closes that gap.

**Files:**

- Modify: `backend/app/services/video/assembly.py` (the `Beat` dataclass at line 22, `compute_timeline`, and `assemble_project`)
- Test: `backend/tests/test_assembly_timeline.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_assembly_timeline.py`:

```python
def test_compute_timeline_records_clip_id():
    """Beats carry the id of the clip they came from, so assemble_project can
    write timeline positions back without re-deriving the filter predicate."""
    from app.services.video.assembly import compute_timeline

    class _Clip:
        def __init__(self, cid, order, url, duration):
            self.id = cid
            self.sequence_order = order
            self.video_url = url
            self.duration_ms = duration
            self.trim_start_ms = None
            self.trim_end_ms = None
            self.segment_id = None

    clips = [
        _Clip("c-b", 1, "/static/video/assets/b.mp4", 3000),
        _Clip("c-a", 0, "/static/video/assets/a.mp4", 2000),
        _Clip("c-skip", 2, None, 4000),
    ]

    beats = compute_timeline(clips, [], "/root", "/audio")

    assert [b.clip_id for b in beats] == ["c-a", "c-b"]
    assert [b.start_ms for b in beats] == [0, 2000]
    assert [b.window_ms for b in beats] == [2000, 3000]
```

- [ ] **Step 2: Run it and watch it fail**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest tests/test_assembly_timeline.py -v -k clip_id
```

Expected: FAIL — `AttributeError: 'Beat' object has no attribute 'clip_id'`.

- [ ] **Step 3: Add the field**

In `backend/app/services/video/assembly.py`, change the typing import from:

```python
from typing import List, Optional
```

to:

```python
from typing import Any, List, Optional
```

Then change the dataclass. The new field goes **last, with a default**, so the nine existing positional `Beat(...)` constructions in `test_assembly_integration.py` and `test_assembly_subtitles.py` keep working:

```python
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
```

In `compute_timeline`, the `Beat(...)` call already uses keyword arguments; add one more:

```python
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
```

- [ ] **Step 4: Run it and watch it pass**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest tests/test_assembly_timeline.py -v
```

Expected: PASS, every test in the file green.

- [ ] **Step 5: Write the failing test for the write-back**

Append to `backend/tests/test_assembly_timeline.py`:

```python
def test_apply_timeline_positions_writes_back_to_clips():
    """assemble_project uses this to stamp each clip's place on the timeline."""
    from app.services.video.assembly import Beat, apply_timeline_positions

    class _Clip:
        def __init__(self, cid):
            self.id = cid
            self.timeline_start_ms = None
            self.timeline_end_ms = None

    a, b = _Clip("c-a"), _Clip("c-b")
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

    class _Clip:
        def __init__(self, cid):
            self.id = cid
            self.timeline_start_ms = 999
            self.timeline_end_ms = 999

    kept, skipped = _Clip("c-a"), _Clip("c-skip")
    beats = [Beat("p1", None, "", 0, 2000, 0, 0, 0, None, clip_id="c-a")]

    apply_timeline_positions([kept, skipped], beats)

    assert (kept.timeline_start_ms, kept.timeline_end_ms) == (0, 2000)
    assert (skipped.timeline_start_ms, skipped.timeline_end_ms) == (None, None)
```

- [ ] **Step 6: Run it and watch it fail**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest tests/test_assembly_timeline.py -v -k apply_timeline
```

Expected: FAIL — `ImportError: cannot import name 'apply_timeline_positions'`.

- [ ] **Step 7: Implement it**

In `backend/app/services/video/assembly.py`, add this function immediately after `compute_timeline`:

```python
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
```

- [ ] **Step 8: Run it and watch it pass**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest tests/test_assembly_timeline.py -v
```

Expected: PASS.

- [ ] **Step 9: Call it from `assemble_project`**

In the same file, inside `assemble_project`, add the call just before the existing `brief = dict(project.video_brief or {})` line, so the tail of the function reads:

```python
    url = f"/static/video/{filename}"
    apply_timeline_positions(project.video_clips, beats)
    brief = dict(project.video_brief or {})
    brief["video_master_url"] = url
    project.video_brief = brief
    await db.commit()
    return url
```

- [ ] **Step 10: Run the whole backend suite**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest -q
```

Expected: `5 failed, 84 passed` — the same 5 stale failures, 3 new passes.

- [ ] **Step 11: Rebuild the demo animatic so the DB carries real timeline positions**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe scripts/assemble_demo.py
```

Expected: it prints the assembled path and a ~23.87s duration, same as before.

- [ ] **Step 12: Commit**

```bash
git add backend/app/services/video/assembly.py backend/tests/test_assembly_timeline.py
git commit -m "feat(video): persist per-clip timeline positions during assembly

The timeline_start_ms/timeline_end_ms columns existed but nothing wrote
them, so the studio clip strip had no positions to seek to.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: `GET /projects/{id}/video/clips`

**Files:**

- Modify: `backend/app/schemas/video.py`
- Modify: `backend/app/api/routes/video.py`
- Create: `backend/tests/test_video_clips_route.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_video_clips_route.py`:

```python
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
```

- [ ] **Step 2: Run it and watch it fail**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest tests/test_video_clips_route.py -v
```

Expected: FAIL — the route does not exist, so the bodies do not match (`KeyError: 'clips'` / `405`).

- [ ] **Step 3: Add the response schema**

Append to `backend/app/schemas/video.py`:

```python
class VideoClipsResponse(BaseModel):
    """Everything the studio's Video tab needs in one read."""
    clips: list[VideoClipRead] = []
    video_brief: Optional[dict] = None
    subtitle_style: Optional[dict] = None
```

- [ ] **Step 4: Add the route**

In `backend/app/api/routes/video.py`, add the import near the other `app.` imports:

```python
from app.schemas.video import VideoClipsResponse
```

and add this route **above** the existing `@router.post("/{project_id}/video/export")`:

```python
@router.get("/{project_id}/video/clips", response_model=VideoClipsResponse)
async def list_video_clips(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Clips in running order, plus the project-level visual direction."""
    project = await _get_owned_project(db, project_id, current_user)
    clips = sorted(project.video_clips or [], key=lambda c: c.sequence_order)
    return VideoClipsResponse(
        clips=clips,
        video_brief=project.video_brief,
        subtitle_style=project.subtitle_style,
    )
```

- [ ] **Step 5: Run it and watch it pass**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest tests/test_video_clips_route.py -v
```

Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/video.py backend/app/schemas/video.py backend/tests/test_video_clips_route.py
git commit -m "feat(video): add GET /projects/{id}/video/clips

Returns clips in sequence order plus video_brief and subtitle_style, so
the studio's Video tab loads in one request.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 3: Campaign medium and subtitle-style persistence

The spec says to extend the existing project `PATCH`. There isn't one — `projects.py` only has `PATCH` routes for segments. So this task adds `PATCH /projects/{project_id}` for project-level settings, and accepts `medium` at creation.

**Files:**

- Modify: `backend/app/schemas/project.py`
- Modify: `backend/app/api/routes/projects.py`
- Modify: `backend/scripts/seed_makeawish_demo.py`
- Create: `backend/tests/test_project_settings_route.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_project_settings_route.py`:

```python
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
```

- [ ] **Step 2: Run it and watch it fail**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest tests/test_project_settings_route.py -v
```

Expected: FAIL — `405 Method Not Allowed`.

- [ ] **Step 3: Add the schemas**

In `backend/app/schemas/project.py`, add `medium` to `ProjectCreate`, immediately after the `speaker_preset` field:

```python
    # "audio" (default) or "video". Persisted into target_audience["medium"];
    # the key's absence means audio, so existing campaigns are untouched.
    medium: Optional[Literal["audio", "video"]] = "audio"
```

and append this class at the end of the file:

```python
class ProjectSettingsUpdate(BaseModel):
    """Project-level settings the studio can change after creation."""
    medium: Optional[Literal["audio", "video"]] = None
    subtitle_style: Optional[Dict[str, Any]] = None
```

- [ ] **Step 4: Persist `medium` at creation**

In `backend/app/api/routes/projects.py`, inside `create_project`, add one key to the `target_audience` dict:

```python
        target_audience={
            "audience": project_in.target_audience,
            "emotion": project_in.primary_emotion,
            "cause": project_in.cause,
            "organization_name": project_in.organization_name,
            "script_length": project_in.script_length,
            "messaging_strategy": project_in.messaging_strategy,
            "medium": project_in.medium or "audio",
        },
```

- [ ] **Step 5: Add the PATCH route**

In the same file, add `ProjectSettingsUpdate` to the existing `from app.schemas.project import ...` line, then add this route immediately after `get_project` and before `@router.post("/{project_id}/export")`:

```python
@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project_settings(
    project_id: uuid.UUID,
    body: ProjectSettingsUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Update project-level settings (campaign medium, subtitle style)."""
    stmt = (
        select(Project)
        .where(Project.id == project_id, Project.user_id == current_user.id)
        .options(selectinload(Project.segments))
    )
    project = (await db.execute(stmt)).scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if body.medium is not None:
        # target_audience is a JSON column — replace the dict. Mutating in place
        # does not mark the attribute dirty and the write is silently dropped.
        audience = dict(project.target_audience or {})
        audience["medium"] = body.medium
        project.target_audience = audience

    if body.subtitle_style is not None:
        project.subtitle_style = dict(body.subtitle_style)

    await db.commit()
    project.segments.sort(key=lambda s: s.sequence_order)
    return project
```

- [ ] **Step 6: Run it and watch it pass**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest tests/test_project_settings_route.py -v
```

Expected: 6 passed.

- [ ] **Step 7: Seed the demo campaign as a video campaign**

In `backend/scripts/seed_makeawish_demo.py`, add `"medium": "video"` to the `target_audience` dict in the `Project(...)` construction:

```python
            target_audience={
                "audience": "Existing mid-level donors, ages 40-65",
                "emotion": "hope",
                "cause": "Granting wishes to children with critical illnesses",
                "organization_name": "Make-A-Wish",
                "script_length": "45s",
                "messaging_strategy": "Single-story arc: confinement, imagination, wish "
                                      "granted, joy, ask. Hope-forward, never pity-forward.",
                "medium": "video",
            },
```

- [ ] **Step 8: Set it on the live demo campaign without re-seeding**

Re-seeding destroys the generated narration, so patch the existing row instead:

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -c "
import asyncio
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.project import Project

async def main():
    async with SessionLocal() as db:
        p = (await db.execute(select(Project).where(Project.title == 'Make-A-Wish (Demo)'))).scalars().first()
        if p is None:
            print('demo project not found'); return
        ta = dict(p.target_audience or {}); ta['medium'] = 'video'; p.target_audience = ta
        await db.commit()
        print('medium =', p.target_audience.get('medium'))

asyncio.run(main())
"
```

Expected output: `medium = video`.

- [ ] **Step 9: Run the whole backend suite**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest -q
```

Expected: `5 failed, 90 passed`.

- [ ] **Step 10: Commit**

```bash
git add backend/app/api/routes/projects.py backend/app/schemas/project.py backend/scripts/seed_makeawish_demo.py backend/tests/test_project_settings_route.py
git commit -m "feat(projects): campaign medium + project settings PATCH

medium lives at target_audience.medium so absent means audio and no
migration is needed. PATCH also persists subtitle_style for the video tab.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: Frontend video types

**Files:**

- Create: `frontend/types/video.ts`
- Modify: `frontend/types/studio.ts`

- [ ] **Step 1: Create the types file**

Create `frontend/types/video.ts`:

```typescript
export type CampaignMedium = 'audio' | 'video';

export type StudioTab = 'audio' | 'video';

export type VideoClipStatus = 'pending' | 'generating' | 'ready' | 'failed';

export type VideoSourceType = 'generated' | 'asset' | 'uploaded';

export interface VideoClip {
    id: string;
    project_id: string;
    segment_id?: string | null;
    sequence_order: number;
    source_type: VideoSourceType;
    status: VideoClipStatus;
    prompt?: string | null;
    video_url?: string | null;
    duration_ms?: number | null;
    trim_start_ms?: number | null;
    trim_end_ms?: number | null;
    timeline_start_ms?: number | null;
    timeline_end_ms?: number | null;
}

export interface VideoBrief {
    style_prompt?: string | null;
    character_sheet?: string | null;
    video_master_url?: string | null;
}

export interface SubtitleStyle {
    enabled: boolean;
    font_size: number;
    position: 'bottom' | 'top' | 'center';
    color: string;
}

export const DEFAULT_SUBTITLE_STYLE: SubtitleStyle = {
    enabled: true,
    font_size: 54,
    position: 'bottom',
    color: 'FFFFFF',
};

export type VideoExportStatus = 'idle' | 'running' | 'ready' | 'failed';

export interface VideoExportState {
    status: VideoExportStatus;
    url: string | null;
    error: string | null;
}

export const IDLE_EXPORT: VideoExportState = { status: 'idle', url: null, error: null };
```

- [ ] **Step 2: Re-export from the existing types barrel**

Append to `frontend/types/studio.ts`:

```typescript
export type {
    CampaignMedium,
    StudioTab,
    VideoClip,
    VideoClipStatus,
    VideoSourceType,
    VideoBrief,
    SubtitleStyle,
    VideoExportStatus,
    VideoExportState,
} from './video';
export { DEFAULT_SUBTITLE_STYLE, IDLE_EXPORT } from './video';
```

- [ ] **Step 3: Typecheck**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/types/video.ts frontend/types/studio.ts
git commit -m "feat(studio): add video clip and export types

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5: Studio store — the video slice

**Files:**

- Modify: `frontend/store/studioStore.ts`

- [ ] **Step 1: Extend the imports**

Change the top of `frontend/store/studioStore.ts` to:

```typescript
import { create } from 'zustand';
import {
    ScriptSegment,
    VoiceProfile,
    CampaignMedium,
    StudioTab,
    VideoClip,
    VideoBrief,
    SubtitleStyle,
    VideoExportState,
} from '../types/studio';
import { IDLE_EXPORT } from '../types/video';
```

- [ ] **Step 2: Extend the state interface**

Add these fields to `interface StudioState`, after `generatingSegments`:

```typescript
    // Video State
    medium: CampaignMedium;
    activeTab: StudioTab;
    videoClips: VideoClip[];
    videoBrief: VideoBrief | null;
    subtitleStyle: SubtitleStyle | null;
    videoExport: VideoExportState;
    activeClipId: string | null;
```

and these to the actions block, after `setGeneratingSegment`:

```typescript
    setActiveTab: (tab: StudioTab) => void;
    setVideoClips: (clips: VideoClip[]) => void;
    setVideoBrief: (brief: VideoBrief | null) => void;
    setSubtitleStyle: (style: SubtitleStyle | null) => void;
    setVideoExport: (state: VideoExportState) => void;
    setActiveClip: (id: string | null) => void;
```

- [ ] **Step 3: Add the initial state**

In the `create<StudioState>(...)` body, after `generatingSegments: {},`:

```typescript
    medium: 'audio',
    activeTab: 'audio',
    videoClips: [],
    videoBrief: null,
    subtitleStyle: null,
    videoExport: IDLE_EXPORT,
    activeClipId: null,
```

- [ ] **Step 4: Add the actions**

After the existing `setGeneratingSegment` action:

```typescript
    setActiveTab: (activeTab) => set({ activeTab }),
    setVideoClips: (videoClips) => set({ videoClips }),
    setVideoBrief: (videoBrief) => set({ videoBrief }),
    setSubtitleStyle: (subtitleStyle) => set({ subtitleStyle }),
    setVideoExport: (videoExport) => set({ videoExport }),
    setActiveClip: (activeClipId) => set({ activeClipId }),
```

- [ ] **Step 5: Read `medium` in `fetchProjectData`**

Change the final `set({ ... })` call inside `fetchProjectData` to:

```typescript
            set({
                script: mappedScript,
                originalScript,
                dirtySegments: {},
                audioUrl: null,
                activeSegmentId: null,
                isPlaying: false,
                generatingSegments: {},
                saveStatus: 'idle',
                // Absent means audio, so campaigns created before the video work
                // render with no tab bar at all.
                medium: project.target_audience?.medium === 'video' ? 'video' : 'audio',
                activeTab: 'audio',
                activeClipId: null,
            });
```

This deliberately does NOT reset `videoClips` or `videoExport` — those are owned by the video fetch in Task 11, and clearing them here would race the poller.

- [ ] **Step 6: Typecheck**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 7: Confirm the existing suite is no worse**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx jest
```

Expected: still `Tests: 6 failed, 1 passed` — unchanged.

- [ ] **Step 8: Commit**

```bash
git add frontend/store/studioStore.ts
git commit -m "feat(studio): add video slice to studioStore

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 6: `useVideoExport` — the assemble/poll state machine

Kept as a standalone hook so the polling logic is testable without a media element.

**Files:**

- Create: `frontend/hooks/useVideoExport.ts`
- Create: `frontend/hooks/useVideoExport.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/hooks/useVideoExport.test.ts`:

```typescript
import { renderHook, act, waitFor } from '@testing-library/react'
import { useVideoExport } from './useVideoExport'

jest.mock('@/lib/api', () => ({
    apiFetch: jest.fn(),
}))

import { apiFetch } from '@/lib/api'

const mockApiFetch = apiFetch as jest.Mock

function ok(body: unknown) {
    return { ok: true, json: async () => body }
}

function fail(status: number, body: unknown) {
    return { ok: false, status, json: async () => body }
}

describe('useVideoExport', () => {
    beforeEach(() => {
        jest.clearAllMocks()
        jest.useFakeTimers()
    })

    afterEach(() => {
        jest.runOnlyPendingTimers()
        jest.useRealTimers()
    })

    it('reports ready and exposes the url when the first status read is already ready', async () => {
        mockApiFetch.mockResolvedValue(
            ok({ status: 'ready', video_master_url: '/static/video/a.mp4', error: null })
        )

        const { result } = renderHook(() => useVideoExport('p1', 'tok'))

        await act(async () => { await result.current.refresh() })

        expect(result.current.state.status).toBe('ready')
        expect(result.current.state.url).toBe('/static/video/a.mp4')
    })

    it('goes running on assemble, then ready once the poll flips', async () => {
        mockApiFetch
            .mockResolvedValueOnce(ok({ status: 'running', message: 'Assembly started.' }))
            .mockResolvedValueOnce(ok({ status: 'running', video_master_url: null, error: null }))
            .mockResolvedValueOnce(ok({ status: 'ready', video_master_url: '/static/video/a.mp4', error: null }))

        const { result } = renderHook(() => useVideoExport('p1', 'tok'))

        await act(async () => { await result.current.assemble() })
        expect(result.current.state.status).toBe('running')

        await act(async () => { jest.advanceTimersByTime(2000) })
        await act(async () => { jest.advanceTimersByTime(2000) })

        await waitFor(() => expect(result.current.state.status).toBe('ready'))
        expect(result.current.state.url).toBe('/static/video/a.mp4')
    })

    it('surfaces the endpoint error string when assembly is rejected', async () => {
        mockApiFetch.mockResolvedValueOnce(
            fail(400, { detail: 'Clips not ready: scene 3, 5.' })
        )

        const { result } = renderHook(() => useVideoExport('p1', 'tok'))

        await act(async () => { await result.current.assemble() })

        expect(result.current.state.status).toBe('failed')
        expect(result.current.state.error).toContain('scene 3, 5')
    })

    it('surfaces a failure reported by the poll', async () => {
        mockApiFetch
            .mockResolvedValueOnce(ok({ status: 'running' }))
            .mockResolvedValueOnce(ok({ status: 'failed', video_master_url: null, error: 'ffmpeg exploded' }))

        const { result } = renderHook(() => useVideoExport('p1', 'tok'))

        await act(async () => { await result.current.assemble() })
        await act(async () => { jest.advanceTimersByTime(2000) })

        await waitFor(() => expect(result.current.state.status).toBe('failed'))
        expect(result.current.state.error).toBe('ffmpeg exploded')
    })

    it('keeps the previous animatic url playable after a failed re-assembly', async () => {
        mockApiFetch
            .mockResolvedValueOnce(ok({ status: 'ready', video_master_url: '/static/video/old.mp4', error: null }))
            .mockResolvedValueOnce(fail(400, { detail: 'Clips not ready: scene 2.' }))

        const { result } = renderHook(() => useVideoExport('p1', 'tok'))

        await act(async () => { await result.current.refresh() })
        await act(async () => { await result.current.assemble() })

        expect(result.current.state.status).toBe('failed')
        expect(result.current.state.url).toBe('/static/video/old.mp4')
    })

    it('stops polling on unmount', async () => {
        mockApiFetch
            .mockResolvedValueOnce(ok({ status: 'running' }))
            .mockResolvedValue(ok({ status: 'running', video_master_url: null, error: null }))

        const { result, unmount } = renderHook(() => useVideoExport('p1', 'tok'))

        await act(async () => { await result.current.assemble() })
        const callsBefore = mockApiFetch.mock.calls.length

        unmount()
        await act(async () => { jest.advanceTimersByTime(10000) })

        expect(mockApiFetch.mock.calls.length).toBe(callsBefore)
    })

    it('does nothing without a token', async () => {
        const { result } = renderHook(() => useVideoExport('p1', undefined))

        await act(async () => { await result.current.assemble() })

        expect(mockApiFetch).not.toHaveBeenCalled()
    })
})
```

- [ ] **Step 2: Run it and watch it fail**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx jest useVideoExport
```

Expected: FAIL — `Cannot find module './useVideoExport'`.

- [ ] **Step 3: Implement the hook**

Create `frontend/hooks/useVideoExport.ts`:

```typescript
'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { apiFetch } from '@/lib/api';
import type { VideoExportState } from '@/types/video';
import { IDLE_EXPORT } from '@/types/video';

const POLL_MS = 2000;

export function useVideoExport(projectId: string | undefined, token: string | undefined) {
    const [state, setState] = useState<VideoExportState>(IDLE_EXPORT);
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const aliveRef = useRef(true);

    useEffect(() => {
        aliveRef.current = true;
        return () => {
            aliveRef.current = false;
            if (timerRef.current) clearTimeout(timerRef.current);
            timerRef.current = null;
        };
    }, []);

    const readStatus = useCallback(async (): Promise<VideoExportState | null> => {
        if (!projectId || !token) return null;
        const res = await apiFetch(`/projects/${projectId}/video/export`, { token });
        if (!res.ok) return null;
        const body = await res.json();
        return {
            status: body.status ?? 'idle',
            url: body.video_master_url ?? null,
            error: body.error ?? null,
        };
    }, [projectId, token]);

    // A failed assembly must leave any previous animatic playable, so a null
    // url from the server never overwrites a url we already hold.
    const merge = useCallback((next: VideoExportState) => {
        setState(prev => ({ ...next, url: next.url ?? prev.url }));
    }, []);

    const refresh = useCallback(async () => {
        const next = await readStatus();
        if (next && aliveRef.current) merge(next);
    }, [readStatus, merge]);

    const poll = useCallback(() => {
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(async () => {
            if (!aliveRef.current) return;
            const next = await readStatus();
            if (!aliveRef.current) return;
            if (next) {
                merge(next);
                if (next.status === 'running') poll();
            } else {
                poll();
            }
        }, POLL_MS);
    }, [readStatus, merge]);

    const assemble = useCallback(async () => {
        if (!projectId || !token) return;
        setState(prev => ({ status: 'running', url: prev.url, error: null }));
        try {
            const res = await apiFetch(`/projects/${projectId}/video/export`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                token,
            });
            if (!res.ok) {
                const body = await res.json().catch(() => ({}));
                const detail = typeof body?.detail === 'string'
                    ? body.detail
                    : 'Assembly could not be started.';
                if (aliveRef.current) {
                    setState(prev => ({ status: 'failed', url: prev.url, error: detail }));
                }
                return;
            }
            if (aliveRef.current) poll();
        } catch (e: any) {
            if (aliveRef.current) {
                setState(prev => ({ status: 'failed', url: prev.url, error: e?.message ?? 'Assembly failed.' }));
            }
        }
    }, [projectId, token, poll]);

    return { state, assemble, refresh };
}
```

- [ ] **Step 4: Run it and watch it pass**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx jest useVideoExport
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/hooks/useVideoExport.ts frontend/hooks/useVideoExport.test.ts
git commit -m "feat(studio): add useVideoExport assemble/poll state machine

Polls the export endpoint every 2s, cancels on unmount, and keeps a
previously assembled animatic playable when a re-assembly fails.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 7: `StudioTabs` — the Audio | Video toggle

**Files:**

- Create: `frontend/components/studio/StudioTabs.tsx`
- Create: `frontend/components/studio/StudioTabs.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/components/studio/StudioTabs.test.tsx`:

```typescript
import '@testing-library/jest-dom'
import { render, screen, fireEvent } from '@testing-library/react'
import StudioTabs from './StudioTabs'
import { useStudioStore } from '@/store/studioStore'

jest.mock('@/store/studioStore')

const mockSetActiveTab = jest.fn()

function mockStore(overrides: Record<string, unknown> = {}) {
    (useStudioStore as unknown as jest.Mock).mockReturnValue({
        medium: 'video',
        activeTab: 'audio',
        setActiveTab: mockSetActiveTab,
        ...overrides,
    })
}

describe('StudioTabs', () => {
    beforeEach(() => {
        jest.clearAllMocks()
    })

    it('renders nothing at all for an audio-only campaign', () => {
        mockStore({ medium: 'audio' })

        const { container } = render(<StudioTabs />)

        expect(container).toBeEmptyDOMElement()
        expect(screen.queryByRole('tab', { name: /video/i })).not.toBeInTheDocument()
    })

    it('renders both tabs for a video campaign', () => {
        mockStore()

        render(<StudioTabs />)

        expect(screen.getByRole('tab', { name: /audio/i })).toBeInTheDocument()
        expect(screen.getByRole('tab', { name: /video/i })).toBeInTheDocument()
    })

    it('marks the active tab as selected', () => {
        mockStore({ activeTab: 'video' })

        render(<StudioTabs />)

        expect(screen.getByRole('tab', { name: /video/i })).toHaveAttribute('aria-selected', 'true')
        expect(screen.getByRole('tab', { name: /audio/i })).toHaveAttribute('aria-selected', 'false')
    })

    it('switches tab on click', () => {
        mockStore()

        fireEvent.click(render(<StudioTabs />).getByRole('tab', { name: /video/i }))

        expect(mockSetActiveTab).toHaveBeenCalledWith('video')
    })
})
```

- [ ] **Step 2: Run it and watch it fail**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx jest StudioTabs
```

Expected: FAIL — `Cannot find module './StudioTabs'`.

- [ ] **Step 3: Implement it**

Create `frontend/components/studio/StudioTabs.tsx`:

```tsx
'use client';

import React from 'react';
import { AudioLines, Clapperboard } from 'lucide-react';
import { useStudioStore } from '@/store/studioStore';
import type { StudioTab } from '@/types/video';

const TABS: { value: StudioTab; label: string; Icon: typeof AudioLines }[] = [
    { value: 'audio', label: 'Audio', Icon: AudioLines },
    { value: 'video', label: 'Video', Icon: Clapperboard },
];

const StudioTabs: React.FC = () => {
    const { medium, activeTab, setActiveTab } = useStudioStore();

    // Audio-only campaigns get no tab bar at all — not a disabled tab, nothing.
    if (medium !== 'video') return null;

    return (
        <div role="tablist" aria-label="Studio medium" className="flex gap-0.5 p-0.5 bg-gray-100 rounded-lg">
            {TABS.map(({ value, label, Icon }) => (
                <button
                    key={value}
                    role="tab"
                    aria-selected={activeTab === value}
                    onClick={() => setActiveTab(value)}
                    className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all ${
                        activeTab === value
                            ? 'bg-white text-moore-black shadow-sm'
                            : 'text-moore-mid-gray hover:text-moore-dark-gray'
                    }`}
                >
                    <Icon className="h-3.5 w-3.5" />
                    {label}
                </button>
            ))}
        </div>
    );
};

export default StudioTabs;
```

- [ ] **Step 4: Run it and watch it pass**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx jest StudioTabs
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/studio/StudioTabs.tsx frontend/components/studio/StudioTabs.test.tsx
git commit -m "feat(studio): add Audio | Video tab toggle

Renders nothing for audio-only campaigns, so existing campaigns are
visually identical to today.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 8: `VideoSegmentList` — left column with poster frames

Poster frames are muted `<video>` elements pointed at the clip URL, so the browser paints the first frame. No backend thumbnail generation.

**Files:**

- Create: `frontend/components/studio/VideoSegmentList.tsx`

- [ ] **Step 1: Implement it**

Create `frontend/components/studio/VideoSegmentList.tsx`:

```tsx
'use client';

import React from 'react';
import { useStudioStore } from '@/store/studioStore';
import { API_URL } from '@/lib/config';
import { Film } from 'lucide-react';
import type { VideoClip, VideoClipStatus } from '@/types/video';

export function mediaUrl(url?: string | null): string {
    if (!url) return '';
    if (url.startsWith('http')) return url;
    return `${API_URL.replace(/\/api\/v1$/, '')}${url}`;
}

const STATUS_DOT: Record<VideoClipStatus, string> = {
    ready: 'bg-green-500',
    generating: 'bg-amber-400 animate-pulse',
    pending: 'bg-gray-300',
    failed: 'bg-red-500',
};

const STATUS_LABEL: Record<VideoClipStatus, string> = {
    ready: 'Clip ready',
    generating: 'Clip generating',
    pending: 'Clip not generated yet',
    failed: 'Clip failed',
};

const VideoSegmentList: React.FC = () => {
    const { script, videoClips, activeSegmentId, setActiveSegment, setActiveClip } = useStudioStore();

    const clipFor = (segmentId: string): VideoClip | undefined =>
        videoClips.find(c => c.segment_id === segmentId);

    const handleClick = (segmentId: string) => {
        setActiveSegment(segmentId);
        setActiveClip(clipFor(segmentId)?.id ?? null);
    };

    return (
        <div className="h-full overflow-y-auto p-4 space-y-2">
            <h3 className="text-sm font-semibold text-moore-dark-gray uppercase tracking-wider mb-3">
                Shots
            </h3>

            {script.length === 0 && (
                <p className="text-sm text-moore-mid-gray italic">No segments yet.</p>
            )}

            {script.map((segment, index) => {
                const clip = clipFor(segment.id);
                const status: VideoClipStatus = clip?.status ?? 'pending';
                const isActive = segment.id === activeSegmentId;

                return (
                    <button
                        key={segment.id}
                        onClick={() => handleClick(segment.id)}
                        className={`w-full text-left p-2.5 rounded-xl border flex gap-3 transition-all ${
                            isActive
                                ? 'bg-white border-moore-red/30 shadow-sm ring-1 ring-moore-red/20'
                                : 'bg-white/60 border-transparent hover:bg-white hover:border-gray-200'
                        }`}
                    >
                        <div className="relative flex-shrink-0 w-20 h-[45px] rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center">
                            {clip?.video_url ? (
                                <video
                                    src={mediaUrl(clip.video_url)}
                                    muted
                                    playsInline
                                    preload="metadata"
                                    aria-hidden="true"
                                    className="w-full h-full object-cover pointer-events-none"
                                />
                            ) : (
                                <Film className="w-4 h-4 text-gray-300" />
                            )}
                            <span
                                title={STATUS_LABEL[status]}
                                className={`absolute top-1 right-1 w-2 h-2 rounded-full ring-1 ring-white ${STATUS_DOT[status]}`}
                            />
                        </div>

                        <div className="flex-1 min-w-0">
                            <p className="text-[10px] font-semibold uppercase tracking-wider text-moore-mid-gray">
                                Scene {index + 1}
                            </p>
                            <p className="text-xs leading-relaxed text-moore-black line-clamp-3">
                                {segment.text}
                            </p>
                        </div>
                    </button>
                );
            })}
        </div>
    );
};

export default VideoSegmentList;
```

- [ ] **Step 2: Typecheck**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/studio/VideoSegmentList.tsx
git commit -m "feat(studio): add video segment list with poster frames

Posters are muted <video> elements pointed at the clip URL, so no
backend thumbnail generation is needed.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 9: `VideoPreview` — player, clip strip, and playback teardown

This is the task carrying the known risk from the spec. `WaveformVisualizer`'s unmount-stops-playback fix must be mirrored here, or leaving the studio — or flipping to the Audio tab — leaves video audio playing.

**Files:**

- Create: `frontend/components/studio/VideoPreview.tsx`
- Create: `frontend/components/studio/VideoPreview.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/components/studio/VideoPreview.test.tsx`:

```typescript
import '@testing-library/jest-dom'
import { render, screen, fireEvent } from '@testing-library/react'
import VideoPreview from './VideoPreview'
import { useStudioStore } from '@/store/studioStore'

jest.mock('@/store/studioStore')

const mockAssemble = jest.fn()
const mockSetActiveClip = jest.fn()

function clip(order: number, over: Record<string, unknown> = {}) {
    return {
        id: `c${order}`,
        project_id: 'p1',
        segment_id: `s${order}`,
        sequence_order: order,
        source_type: 'asset',
        status: 'ready',
        prompt: `shot ${order}`,
        video_url: `/static/video/assets/c${order}.mp4`,
        duration_ms: 2000,
        timeline_start_ms: order * 2000,
        timeline_end_ms: (order + 1) * 2000,
        ...over,
    }
}

function mockStore(overrides: Record<string, unknown> = {}) {
    (useStudioStore as unknown as jest.Mock).mockReturnValue({
        videoClips: [clip(1), clip(0), clip(2)],
        script: [
            { id: 's0', text: 'first', start_ms: 0, end_ms: 2000 },
            { id: 's1', text: 'second', start_ms: 2000, end_ms: 4000 },
            { id: 's2', text: 'third', start_ms: 4000, end_ms: 6000 },
        ],
        activeSegmentId: null,
        activeClipId: null,
        setActiveClip: mockSetActiveClip,
        setActiveSegment: jest.fn(),
        ...overrides,
    })
}

describe('VideoPreview', () => {
    beforeEach(() => {
        jest.clearAllMocks()
        window.HTMLMediaElement.prototype.play = jest.fn().mockResolvedValue(undefined)
        window.HTMLMediaElement.prototype.pause = jest.fn()
        window.HTMLMediaElement.prototype.load = jest.fn()
    })

    it('shows the empty state with an assemble button before the first assembly', () => {
        mockStore()

        render(<VideoPreview exportState={{ status: 'idle', url: null, error: null }} onAssemble={mockAssemble} />)

        expect(screen.getByRole('button', { name: /assemble video/i })).toBeInTheDocument()
        expect(screen.queryByTestId('animatic-player')).not.toBeInTheDocument()
    })

    it('triggers assembly from the empty state', () => {
        mockStore()

        render(<VideoPreview exportState={{ status: 'idle', url: null, error: null }} onAssemble={mockAssemble} />)
        fireEvent.click(screen.getByRole('button', { name: /assemble video/i }))

        expect(mockAssemble).toHaveBeenCalled()
    })

    it('renders the player once an animatic url exists', () => {
        mockStore()

        render(<VideoPreview exportState={{ status: 'ready', url: '/static/video/a.mp4', error: null }} onAssemble={mockAssemble} />)

        expect(screen.getByTestId('animatic-player')).toBeInTheDocument()
    })

    it('orders the clip strip by sequence_order regardless of array order', () => {
        mockStore()

        render(<VideoPreview exportState={{ status: 'ready', url: '/static/video/a.mp4', error: null }} onAssemble={mockAssemble} />)

        const ids = screen.getAllByTestId('clip-strip-item').map(el => el.getAttribute('data-clip-id'))
        expect(ids).toEqual(['c0', 'c1', 'c2'])
    })

    it('shows the assembly error and keeps the previous animatic playable', () => {
        mockStore()

        render(<VideoPreview
            exportState={{ status: 'failed', url: '/static/video/old.mp4', error: 'Clips not ready: scene 3.' }}
            onAssemble={mockAssemble}
        />)

        expect(screen.getByText(/clips not ready: scene 3/i)).toBeInTheDocument()
        expect(screen.getByTestId('animatic-player')).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
    })

    it('shows a running indicator while assembling', () => {
        mockStore()

        render(<VideoPreview exportState={{ status: 'running', url: null, error: null }} onAssemble={mockAssemble} />)

        expect(screen.getByText(/assembling/i)).toBeInTheDocument()
    })

    it('pauses the player on unmount', () => {
        mockStore()
        const pause = jest.fn()
        window.HTMLMediaElement.prototype.pause = pause

        const { unmount } = render(
            <VideoPreview exportState={{ status: 'ready', url: '/static/video/a.mp4', error: null }} onAssemble={mockAssemble} />
        )
        unmount()

        expect(pause).toHaveBeenCalled()
    })
})
```

- [ ] **Step 2: Run it and watch it fail**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx jest VideoPreview
```

Expected: FAIL — `Cannot find module './VideoPreview'`.

- [ ] **Step 3: Implement it**

Create `frontend/components/studio/VideoPreview.tsx`:

```tsx
'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, Clapperboard, Film, Loader2, RotateCw } from 'lucide-react';
import { useStudioStore } from '@/store/studioStore';
import { mediaUrl } from './VideoSegmentList';
import type { VideoClip, VideoExportState } from '@/types/video';

interface VideoPreviewProps {
    exportState: VideoExportState;
    onAssemble: () => void;
}

function formatSeconds(ms: number): string {
    const total = Math.round(ms / 1000);
    return `${Math.floor(total / 60)}:${(total % 60).toString().padStart(2, '0')}`;
}

/** Timeline positions are written by assembly. Before the first assembly they
 *  are null, so fall back to a running sum of the clips' natural durations. */
function withPositions(clips: VideoClip[]) {
    let cursor = 0;
    return [...clips]
        .sort((a, b) => a.sequence_order - b.sequence_order)
        .map(clip => {
            const start = clip.timeline_start_ms ?? cursor;
            const end = clip.timeline_end_ms ?? start + (clip.duration_ms ?? 0);
            cursor = end;
            return { clip, start, end };
        });
}

const VideoPreview: React.FC<VideoPreviewProps> = ({ exportState, onAssemble }) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [currentMs, setCurrentMs] = useState(0);
    const { videoClips, script, activeSegmentId, setActiveClip } = useStudioStore();

    const positioned = useMemo(() => withPositions(videoClips), [videoClips]);

    // Mirrors the WaveformVisualizer unmount fix: leaving the studio, or flipping
    // to the Audio tab (which unmounts this component), must stop the audio. pause()
    // alone can leave a buffered stream running, so the source is unloaded too.
    useEffect(() => {
        const el = videoRef.current;
        return () => {
            if (!el) return;
            try { el.pause(); } catch { /* already stopped */ }
            try {
                el.removeAttribute('src');
                el.load();
            } catch { /* teardown races a pending load; nothing to recover */ }
        };
    }, []);

    // Clicking a segment seeks the preview, mirroring how it seeks the waveform.
    useEffect(() => {
        if (!activeSegmentId) return;
        const match = positioned.find(p => p.clip.segment_id === activeSegmentId);
        const el = videoRef.current;
        if (!match || !el || !Number.isFinite(el.duration)) return;
        el.currentTime = match.start / 1000;
        setCurrentMs(match.start);
    }, [activeSegmentId, positioned]);

    const activeStripId = positioned.find(p => currentMs >= p.start && currentMs < p.end)?.clip.id ?? null;
    const totalMs = positioned.length ? positioned[positioned.length - 1].end : 0;
    const textFor = (segmentId?: string | null) =>
        script.find(s => s.id === segmentId)?.text ?? '';

    const hasVideo = !!exportState.url;

    return (
        <div className="w-full h-full p-4 flex flex-col gap-3">
            {exportState.status === 'failed' && exportState.error && (
                <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2">
                    <AlertCircle className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
                    <p className="flex-1 text-xs text-red-700">{exportState.error}</p>
                    <button
                        onClick={onAssemble}
                        className="flex items-center gap-1 rounded-lg border border-red-200 bg-white px-2 py-1 text-[11px] font-medium text-red-700 hover:bg-red-100 transition-colors"
                    >
                        <RotateCw className="h-3 w-3" />
                        Retry
                    </button>
                </div>
            )}

            <div className="flex-1 min-h-0 rounded-2xl bg-black/90 flex items-center justify-center overflow-hidden">
                {hasVideo ? (
                    <video
                        ref={videoRef}
                        data-testid="animatic-player"
                        src={mediaUrl(exportState.url)}
                        controls
                        playsInline
                        preload="metadata"
                        onTimeUpdate={e => setCurrentMs(e.currentTarget.currentTime * 1000)}
                        className="max-w-full max-h-full"
                    />
                ) : exportState.status === 'running' ? (
                    <div className="flex flex-col items-center gap-3 text-white/80">
                        <Loader2 className="h-8 w-8 animate-spin" />
                        <p className="text-sm">Assembling your animatic...</p>
                    </div>
                ) : (
                    <div className="flex flex-col items-center gap-4 px-8 text-center">
                        <Clapperboard className="h-10 w-10 text-white/30" />
                        <p className="text-sm text-white/60">
                            No animatic yet. Assemble the clips and narration into one video.
                        </p>
                        <button
                            onClick={onAssemble}
                            className="flex items-center gap-2 rounded-xl bg-moore-red px-4 py-2 text-sm font-semibold text-white hover:bg-moore-red-dark transition-all active:scale-[0.98]"
                        >
                            <Film className="h-4 w-4" />
                            Assemble video
                        </button>
                    </div>
                )}
            </div>

            <div className="flex-shrink-0">
                <div className="flex items-center justify-between mb-1.5">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-moore-mid-gray">
                        Clips
                    </p>
                    {totalMs > 0 && (
                        <p className="text-[10px] font-mono text-moore-mid-gray tabular-nums">
                            {formatSeconds(totalMs)} total
                        </p>
                    )}
                </div>
                <div className="flex gap-1 overflow-x-auto pb-1">
                    {positioned.map(({ clip, start, end }, index) => (
                        <button
                            key={clip.id}
                            data-testid="clip-strip-item"
                            data-clip-id={clip.id}
                            title={textFor(clip.segment_id)}
                            onClick={() => {
                                setActiveClip(clip.id);
                                const el = videoRef.current;
                                if (el && Number.isFinite(el.duration)) {
                                    el.currentTime = start / 1000;
                                    setCurrentMs(start);
                                }
                            }}
                            className={`flex-shrink-0 w-24 rounded-lg border px-2 py-1.5 text-left transition-all ${
                                clip.id === activeStripId
                                    ? 'border-moore-red bg-moore-red/10'
                                    : 'border-gray-200 bg-white hover:border-gray-300'
                            }`}
                        >
                            <p className="text-[10px] font-semibold text-moore-dark-gray">
                                Scene {index + 1}
                            </p>
                            <p className="text-[10px] font-mono text-moore-mid-gray tabular-nums">
                                {formatSeconds(end - start)}
                            </p>
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default VideoPreview;
```

- [ ] **Step 4: Run it and watch it pass**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx jest VideoPreview
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/studio/VideoPreview.tsx frontend/components/studio/VideoPreview.test.tsx
git commit -m "feat(studio): add animatic preview player and clip strip

Mirrors the WaveformVisualizer unmount-stops-playback fix onto the video
element, so leaving the studio or switching tabs stops the audio.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 10: `VideoInspector` — read-only clip detail + subtitle control

**Files:**

- Create: `frontend/components/studio/VideoInspector.tsx`

- [ ] **Step 1: Implement it**

Create `frontend/components/studio/VideoInspector.tsx`:

```tsx
'use client';

import React, { useState } from 'react';
import { useParams } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import toast from 'react-hot-toast';
import { useStudioStore } from '@/store/studioStore';
import { apiFetch } from '@/lib/api';
import { DEFAULT_SUBTITLE_STYLE } from '@/types/video';
import type { SubtitleStyle } from '@/types/video';

function formatMs(ms?: number | null): string {
    if (ms === null || ms === undefined) return '—';
    return `${(ms / 1000).toFixed(1)}s`;
}

const SOURCE_LABEL: Record<string, string> = {
    generated: 'Generated',
    asset: 'Pre-made asset',
    uploaded: 'Uploaded',
};

const VideoInspector: React.FC = () => {
    const { videoClips, activeClipId, activeSegmentId, script, videoBrief, subtitleStyle, setSubtitleStyle } =
        useStudioStore();
    const { data: session } = useSession();
    const params = useParams();
    const projectId = params?.id as string;
    const [showBible, setShowBible] = useState(false);

    const clip =
        videoClips.find(c => c.id === activeClipId) ??
        videoClips.find(c => c.segment_id === activeSegmentId);
    const segment = script.find(s => s.id === clip?.segment_id);
    const style = subtitleStyle ?? DEFAULT_SUBTITLE_STYLE;

    const persistStyle = async (next: SubtitleStyle) => {
        setSubtitleStyle(next);
        const token = session?.accessToken;
        if (!token || !projectId) return;
        try {
            const res = await apiFetch(`/projects/${projectId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                token,
                body: JSON.stringify({ subtitle_style: next }),
            });
            if (!res.ok) throw new Error('save failed');
        } catch {
            toast.error('Could not save subtitle settings');
        }
    };

    return (
        <div className="h-full p-5 bg-white flex flex-col gap-5 overflow-y-auto">
            <h3 className="text-sm font-semibold text-moore-dark-gray uppercase tracking-wider">
                Clip Inspector
            </h3>

            {!clip ? (
                <p className="text-sm text-moore-mid-gray">
                    Select a shot on the left to see its detail.
                </p>
            ) : (
                <div className="space-y-4">
                    <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 text-[10px] font-semibold uppercase bg-moore-red/10 text-moore-red border border-moore-red/20 rounded-md">
                            {SOURCE_LABEL[clip.source_type] ?? clip.source_type}
                        </span>
                        <span className="text-[11px] text-moore-mid-gray capitalize">{clip.status}</span>
                    </div>

                    <div className="flex gap-3">
                        <div className="flex-1 bg-moore-cream/50 rounded-xl px-3 py-2 border border-gray-100">
                            <p className="text-[10px] text-moore-mid-gray uppercase tracking-wider">Duration</p>
                            <p className="text-sm font-mono text-moore-black">{formatMs(clip.duration_ms)}</p>
                        </div>
                        <div className="flex-1 bg-moore-cream/50 rounded-xl px-3 py-2 border border-gray-100">
                            <p className="text-[10px] text-moore-mid-gray uppercase tracking-wider">Starts at</p>
                            <p className="text-sm font-mono text-moore-black">{formatMs(clip.timeline_start_ms)}</p>
                        </div>
                    </div>

                    {segment && (
                        <div className="space-y-1">
                            <p className="text-[10px] text-moore-mid-gray uppercase tracking-wider">Narration</p>
                            <p className="text-xs leading-relaxed text-moore-dark-gray">{segment.text}</p>
                        </div>
                    )}

                    {clip.prompt && (
                        <div className="space-y-1">
                            <p className="text-[10px] text-moore-mid-gray uppercase tracking-wider">Shot prompt</p>
                            <p className="text-xs leading-relaxed text-moore-mid-gray whitespace-pre-wrap">
                                {clip.prompt}
                            </p>
                        </div>
                    )}
                </div>
            )}

            <div className="border-t border-gray-100 pt-4 space-y-3">
                <div className="flex items-center justify-between">
                    <label className="text-sm font-medium text-moore-dark-gray">Burn in subtitles</label>
                    <input
                        type="checkbox"
                        checked={style.enabled}
                        onChange={e => persistStyle({ ...style, enabled: e.target.checked })}
                        className="h-4 w-4 accent-moore-red"
                    />
                </div>
                <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                        <label className="text-sm font-medium text-moore-dark-gray">Caption size</label>
                        <span className="text-xs text-moore-mid-gray tabular-nums">{style.font_size}</span>
                    </div>
                    <input
                        type="range"
                        min={24} max={80} step={2}
                        value={style.font_size}
                        disabled={!style.enabled}
                        onChange={e => persistStyle({ ...style, font_size: parseInt(e.target.value, 10) })}
                        className="w-full accent-moore-red disabled:opacity-40"
                    />
                </div>
                <p className="text-[10px] text-moore-mid-gray italic">
                    Applies on next assembly — the current video is unchanged.
                </p>
            </div>

            <div className="border-t border-gray-100 pt-4">
                <button
                    onClick={() => setShowBible(v => !v)}
                    className="flex items-center gap-1.5 text-sm font-medium text-moore-dark-gray hover:text-moore-black transition-colors"
                >
                    {showBible ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                    Visual bible
                </button>
                {showBible && (
                    <div className="mt-3 space-y-3">
                        <div className="space-y-1">
                            <p className="text-[10px] text-moore-mid-gray uppercase tracking-wider">Style</p>
                            <p className="text-xs leading-relaxed text-moore-mid-gray whitespace-pre-wrap">
                                {videoBrief?.style_prompt || 'Not set.'}
                            </p>
                        </div>
                        <div className="space-y-1">
                            <p className="text-[10px] text-moore-mid-gray uppercase tracking-wider">Characters</p>
                            <p className="text-xs leading-relaxed text-moore-mid-gray whitespace-pre-wrap">
                                {videoBrief?.character_sheet || 'Not set.'}
                            </p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default VideoInspector;
```

- [ ] **Step 2: Typecheck**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/studio/VideoInspector.tsx
git commit -m "feat(studio): add read-only clip inspector with subtitle control

Subtitle toggle and size write through the project PATCH and are labelled
as applying on next assembly, not to the current video.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 11: Wire the Video tab into the studio page

**Files:**

- Modify: `frontend/app/dashboard/studio/[id]/page.tsx`

- [ ] **Step 1: Add the imports**

At the top of `frontend/app/dashboard/studio/[id]/page.tsx`, add:

```typescript
import StudioTabs from '@/components/studio/StudioTabs';
import VideoSegmentList from '@/components/studio/VideoSegmentList';
import VideoPreview from '@/components/studio/VideoPreview';
import VideoInspector from '@/components/studio/VideoInspector';
import { useVideoExport } from '@/hooks/useVideoExport';
```

and add `Film` to the existing `lucide-react` import so it reads:

```typescript
import { ArrowLeft, Download, Film, Loader2, Keyboard } from 'lucide-react';
```

- [ ] **Step 2: Reorder the hooks and add the export hook**

`useVideoExport` needs `session`, which is currently declared several lines below the store destructure. Replace the opening of the component body:

```typescript
    const params = useParams();
    const projectId = params.id as string;
    const { fetchProjectData, audioUrl, script, generatingSegments } = useStudioStore();
    const [isGenerating, setIsGenerating] = useState(false);
    const [isLoadingProject, setIsLoadingProject] = useState(true);
    const [isAwaitingAudio, setIsAwaitingAudio] = useState(false);
    const { data: session, status } = useSession();
    const [wasRegenerating, setWasRegenerating] = useState(false);
```

with:

```typescript
    const params = useParams();
    const projectId = params.id as string;
    const { data: session, status } = useSession();
    const { fetchProjectData, audioUrl, script, generatingSegments, medium, activeTab } = useStudioStore();
    const videoExport = useVideoExport(projectId, session?.accessToken);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isLoadingProject, setIsLoadingProject] = useState(true);
    const [isAwaitingAudio, setIsAwaitingAudio] = useState(false);
    const [wasRegenerating, setWasRegenerating] = useState(false);
```

- [ ] **Step 3: Load the clips for video campaigns**

Add this effect after the existing keyboard-shortcuts effect:

```typescript
    // Video clips + brief + subtitle style, loaded once per project for video campaigns.
    useEffect(() => {
        let cancelled = false;
        const load = async () => {
            const token = session?.accessToken;
            if (!token || !projectId || medium !== 'video') return;
            try {
                const res = await apiFetch(`/projects/${projectId}/video/clips`, { token });
                if (!res.ok || cancelled) return;
                const data = await res.json();
                const store = useStudioStore.getState();
                store.setVideoClips(data.clips ?? []);
                store.setVideoBrief(data.video_brief ?? null);
                store.setSubtitleStyle(data.subtitle_style ?? null);
            } catch (e) {
                console.error('Failed to load video clips:', e);
            }
        };
        load();
        if (medium === 'video') videoExport.refresh();
        return () => { cancelled = true; };
    }, [projectId, medium, session?.accessToken]);
```

- [ ] **Step 4: Reload clips after a successful assembly**

Assembly stamps `timeline_start_ms`/`timeline_end_ms` onto the clips, so the strip needs a re-read. Add:

```typescript
    // Assembly writes timeline positions onto the clips; re-read them so the clip
    // strip shows real windows rather than the duration_ms fallback.
    useEffect(() => {
        if (videoExport.state.status !== 'ready') return;
        const token = session?.accessToken;
        if (!token || !projectId) return;
        apiFetch(`/projects/${projectId}/video/clips`, { token })
            .then(res => (res.ok ? res.json() : null))
            .then(data => { if (data) useStudioStore.getState().setVideoClips(data.clips ?? []); })
            .catch(() => { /* strip keeps its fallback positions */ });
    }, [videoExport.state.status, projectId, session?.accessToken]);
```

- [ ] **Step 5: Stop playback on every tab change**

Belt and braces on top of each visualizer's own unmount teardown — the global `isPlaying` flag survives the component swap:

```typescript
    useEffect(() => {
        useStudioStore.getState().setIsPlaying(false);
    }, [activeTab]);
```

- [ ] **Step 6: Put the tab bar in the header**

In the header's left-hand group, immediately after the `</h1>`, add:

```tsx
                    {medium === 'video' && <div className="h-5 w-px bg-gray-200" />}
                    <StudioTabs />
```

- [ ] **Step 7: Make the export button contextual**

Replace the entire header `<div className="flex gap-2">` block with:

```tsx
                <div className="flex gap-2">
                    <button
                        onClick={() => setShowShortcuts(prev => !prev)}
                        className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm text-moore-mid-gray border border-gray-200 hover:bg-gray-50 transition-colors"
                        title="Keyboard shortcuts (?)"
                    >
                        <Keyboard className="h-4 w-4" />
                    </button>

                    {activeTab === 'video' ? (
                        <button
                            onClick={videoExport.assemble}
                            disabled={videoExport.state.status === 'running'}
                            className="flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium bg-moore-red text-white hover:bg-moore-red-dark shadow-sm transition-all disabled:opacity-50"
                        >
                            {videoExport.state.status === 'running' ? (
                                <><Loader2 className="h-4 w-4 animate-spin" /> Assembling...</>
                            ) : (
                                <><Film className="h-4 w-4" /> {videoExport.state.url ? 'Re-assemble' : 'Assemble video'}</>
                            )}
                        </button>
                    ) : (
                        <>
                            {audioUrl && (
                                <button
                                    onClick={handleDownload}
                                    className="flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium bg-green-50 text-green-700 border border-green-200 hover:bg-green-100 transition-all"
                                >
                                    <Download className="h-4 w-4" />
                                    Download WAV
                                </button>
                            )}
                            <button
                                onClick={audioUrl ? handleDownload : handleGenerateFullAudio}
                                disabled={isGenerating}
                                className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition-all ${
                                    audioUrl
                                        ? 'bg-white text-moore-mid-gray border border-gray-200 hover:bg-gray-50'
                                        : 'bg-moore-red text-white hover:bg-moore-red-dark shadow-sm'
                                } disabled:opacity-50`}
                            >
                                {isGenerating ? (
                                    <><Loader2 className="h-4 w-4 animate-spin" /> Exporting...</>
                                ) : audioUrl ? (
                                    'Re-export'
                                ) : (
                                    <><Download className="h-4 w-4" /> Export & Download</>
                                )}
                            </button>
                        </>
                    )}
                </div>
```

- [ ] **Step 8: Swap the three columns by tab**

Replace the `<div className="flex flex-1 overflow-hidden">` block with:

```tsx
                <div className="flex flex-1 overflow-hidden">
                    {/* Left Column - 30% */}
                    <div className="w-[30%] h-full flex flex-col border-r border-gray-200">
                        {activeTab === 'video' ? <VideoSegmentList /> : <ScriptEditor />}
                    </div>

                    {/* Center Column - 45% */}
                    <div className="w-[45%] h-full flex flex-col relative bg-white">
                        {activeTab === 'video' ? (
                            <VideoPreview exportState={videoExport.state} onAssemble={videoExport.assemble} />
                        ) : (
                            <div className="flex-1 p-6 flex items-center justify-center">
                                <WaveformVisualizer />
                            </div>
                        )}
                    </div>

                    {/* Right Column - 25% */}
                    <div className="w-[25%] h-full border-l border-gray-200 bg-white">
                        {activeTab === 'video' ? <VideoInspector /> : <InspectorPanel />}
                    </div>
                </div>
```

Because the two centre components are mutually exclusive, switching tabs unmounts the other one — which is exactly what makes each one's teardown effect stop its own playback. Do NOT convert this into a hide-with-CSS approach; that would reintroduce the bug the spec flags as the known risk.

- [ ] **Step 9: Typecheck, lint, build**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx tsc --noEmit && npm run lint && npm run build
```

Expected: no type errors; lint warnings only if they already existed; build succeeds.

- [ ] **Step 10: Commit**

```bash
git add "frontend/app/dashboard/studio/[id]/page.tsx"
git commit -m "feat(studio): wire the Video tab into the studio shell

Reuses the 30/45/25 columns and swaps their contents by tab. Mutually
exclusive rendering means switching tabs unmounts the other player, which
is what stops its playback.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 12: Campaign medium at creation + dashboard badge

**Files:**

- Modify: `frontend/components/dashboard/create-campaign-modal.tsx`
- Modify: `frontend/components/dashboard/CampaignList.tsx`

- [ ] **Step 1: Add the medium state**

In `frontend/components/dashboard/create-campaign-modal.tsx`, next to the existing `selectedVoice` state, add:

```typescript
    const [medium, setMedium] = React.useState<'audio' | 'video'>('audio')
```

- [ ] **Step 2: Send it in the payload**

In the submit handler, immediately before the `apiFetch('/projects', ...)` call, add:

```typescript
            payload.medium = medium;
```

- [ ] **Step 3: Add the toggle to the form**

Immediately above the Voice block (the one commented `{/* Voice — applied to every segment... */}`), insert:

```tsx
                {/* Medium — video campaigns get an Audio | Video tab in the studio.
                    Audio-only campaigns render exactly as they do today. */}
                <div className="space-y-1.5">
                    <label className="text-sm font-medium text-moore-dark-gray">Deliverable</label>
                    <div className="flex gap-0.5 p-0.5 bg-gray-100 rounded-lg">
                        {(['audio', 'video'] as const).map(value => (
                            <button
                                key={value}
                                type="button"
                                onClick={() => setMedium(value)}
                                className={`flex-1 text-[11px] py-1.5 rounded-md font-medium transition-all ${
                                    medium === value
                                        ? 'bg-white text-moore-black shadow-sm'
                                        : 'text-moore-mid-gray hover:text-moore-dark-gray'
                                }`}
                            >
                                {value === 'audio' ? 'Audio only' : 'Audio + video'}
                            </button>
                        ))}
                    </div>
                    <p className="text-[11px] text-moore-mid-gray">
                        Video campaigns gain a Video tab in the studio for previsualisation.
                    </p>
                </div>
```

- [ ] **Step 4: Add the badge to the campaign card**

In `frontend/components/dashboard/CampaignList.tsx`, widen the `target_audience` type on line 15:

```typescript
    target_audience: { audience?: string; emotion?: string; medium?: string };
```

and immediately after the existing status pill (the `<span className={...status.color}>` block around line 166), add:

```tsx
                                {campaign.target_audience?.medium === 'video' && (
                                    <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200">
                                        Video
                                    </span>
                                )}
```

- [ ] **Step 5: Typecheck and build**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx tsc --noEmit && npm run build
```

Expected: both succeed.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/dashboard/create-campaign-modal.tsx frontend/components/dashboard/CampaignList.tsx
git commit -m "feat(dashboard): campaign medium toggle and video badge

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 13: Full verification

- [ ] **Step 1: Backend suite**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest -q
```

Expected: `5 failed, 90 passed`. Exactly the same 5 stale names as the baseline. If a sixth appears, stop and fix it before continuing.

- [ ] **Step 2: Frontend suite**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npx jest
```

Expected: the pre-existing `6 failed` from `InspectorPanel.test.tsx` and `ScriptEditor.test.tsx`, plus 18 new passes across `useVideoExport.test.ts` (7), `StudioTabs.test.tsx` (4), and `VideoPreview.test.tsx` (7).

- [ ] **Step 3: Production build**

```bash
cd "D:/Repo/Aria Appeal/frontend" && npm run build
```

Expected: success.

- [ ] **Step 4: Manual check — the audio-only regression (the top success criterion)**

Start both servers:

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/Activate.ps1; uvicorn app.main:app --reload
```

```bash
cd "D:/Repo/Aria Appeal/frontend" && npm run dev
```

Open any campaign that is NOT `Make-A-Wish (Demo)`. Confirm:

- There is **no tab bar** in the header — not a disabled tab, not an empty one.
- The header shows `Export & Download` / `Re-export` exactly as before.
- The waveform, script editor and inspector all behave as before.

- [ ] **Step 5: Manual check — the video campaign**

Open `Make-A-Wish (Demo)`. Confirm:

- The header shows `Audio | Video`, defaulting to Audio, and the Audio tab looks unchanged.
- Switching to Video shows six shots with poster frames on the left, the assembled animatic in the centre, and a clip strip beneath it.
- The animatic plays with narration and burned-in captions.
- Clicking a shot on the left seeks the player to that scene.
- Clicking a clip in the strip seeks the player, and the strip highlights the current shot as it plays.
- The inspector shows the clip's source badge, duration, timeline position and shot prompt, and the visual bible expands.

- [ ] **Step 6: Manual check — playback teardown (the known risk)**

- Play the animatic, then click the **Audio** tab. Audio must stop immediately.
- Play the animatic, then click **Dashboard**. Audio must stop immediately.
- Play the audio waveform, then switch to **Video**. Audio must stop immediately.

- [ ] **Step 7: Manual check — assembly from the studio**

Click **Re-assemble**. The button shows `Assembling...`, the status polls, and the player swaps to the new file when it flips to ready.

Then exercise the failure path — set one clip to pending:

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -c "
import asyncio
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.project import Project
from app.models.video_clip import VideoClip, VideoClipStatus

async def main():
    async with SessionLocal() as db:
        p = (await db.execute(select(Project).where(Project.title == 'Make-A-Wish (Demo)'))).scalars().first()
        c = (await db.execute(select(VideoClip).where(VideoClip.project_id == p.id, VideoClip.sequence_order == 2))).scalars().first()
        c.status = VideoClipStatus.PENDING
        await db.commit()
        print('scene 3 set to pending')

asyncio.run(main())
"
```

Click **Re-assemble** again: the error banner must name scene 3, offer Retry, and the previously assembled animatic must still be playable. Then restore it:

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -c "
import asyncio
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.project import Project
from app.models.video_clip import VideoClip, VideoClipStatus

async def main():
    async with SessionLocal() as db:
        p = (await db.execute(select(Project).where(Project.title == 'Make-A-Wish (Demo)'))).scalars().first()
        c = (await db.execute(select(VideoClip).where(VideoClip.project_id == p.id, VideoClip.sequence_order == 2))).scalars().first()
        c.status = VideoClipStatus.READY
        await db.commit()
        print('scene 3 restored to ready')

asyncio.run(main())
"
```

- [ ] **Step 8: Push**

```bash
git status
git push origin feat/video-previs
```

---

## Success criteria (from the spec)

- An audio-only campaign is visually and behaviourally identical to today — verified in Task 13 Step 4.
- A video campaign shows `Audio | Video`, and the Video tab plays the assembled animatic with narration and burned-in captions — Task 13 Step 5.
- Assembly can be triggered and its progress followed from the studio — Task 13 Step 7.
- Switching tabs or leaving the studio stops playback — Task 13 Step 6.
