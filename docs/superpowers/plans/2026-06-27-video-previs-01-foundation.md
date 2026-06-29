# Video Previsualization — Plan 1: Backend Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the backend foundation for the video previsualization feature — environment prerequisites, provider config, the `VideoClip` data model with project-level video fields, and the database migration — so later plans can build the provider, generation, assembly, and editor on top.

**Architecture:** Pure backend, no runtime video work yet. Adds one SQLAlchemy model (`videoclip` table), two JSON columns on `Project`, Pydantic schemas, config fields on `SystemSettings`, and an Alembic migration. Mirrors existing patterns (lowercase table names, `config_manager`, the audio model layout). Tests introspect SQLAlchemy metadata and Pydantic defaults — no live DB required except for the migration verification step.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy (async), Pydantic v2, Alembic, pytest, ffmpeg, `google-genai`.

**Source spec:** `docs/superpowers/specs/2026-06-26-video-previsualization-design.md`

---

## Pre-flight

This plan should be executed on a **dedicated branch**, not the current `feat/voice-selection-and-video-design` PR branch.

- [ ] **Step 0: Create a working branch from main**

```bash
cd "D:/Repo/Aria Appeal"
git fetch origin
git checkout -b feat/video-previs main
git branch --show-current
```
Expected: `feat/video-previs`

---

## Task 1: Environment prerequisites (ffmpeg, Gemini SDK, static dirs)

**Files:**
- Modify: `.gitignore`
- No source/test files (environment + verification only)

- [ ] **Step 1: Install ffmpeg and ffprobe**

On Windows, install via winget (preferred):
```bash
winget install --id Gyan.FFmpeg -e
```
If winget is unavailable, download a static build from https://www.gyan.dev/ffmpeg/builds/ (the "release full" 7z), extract, and add its `bin/` folder to the system PATH.

- [ ] **Step 2: Verify ffmpeg and ffprobe are on PATH**

Run (open a fresh shell so PATH changes take effect):
```bash
ffmpeg -version
ffprobe -version
```
Expected: both print a version banner (e.g. `ffmpeg version 7.x`). If "command not found", PATH is not updated — fix before continuing; the entire video feature depends on these.

- [ ] **Step 3: Install the Gemini SDK into the backend venv**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pip install google-genai
```
Expected: installs `google-genai` and dependencies.

- [ ] **Step 4: Verify the SDK imports**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -c "from google import genai; print('genai ok')"
```
Expected: prints `genai ok`.

- [ ] **Step 5: Create the static video directories**

```bash
cd "D:/Repo/Aria Appeal/backend"
mkdir -p static/video/assets static/video/uploads static/video/clips
```
(`clips/` holds normalized generated/asset clips; `uploads/` holds raw user uploads; `assets/` holds pre-made demo clips. The existing static mount in `app/main.py` serves the whole `static/` tree at `/static`, so `/static/video/...` resolves automatically — no mount change needed.)

- [ ] **Step 6: Gitignore generated video media**

Add these lines to `.gitignore` under the `# Build artifacts` section (after the existing `backend/static/voice_uploads/` line):
```
/static/video/
backend/static/video/
```

- [ ] **Step 7: Add `requirements.txt` entry for the SDK (if the repo tracks one)**

```bash
cd "D:/Repo/Aria Appeal/backend"
ls requirements.txt 2>/dev/null && echo "google-genai" >> requirements.txt || echo "no requirements.txt — skip"
```
If a `requirements.txt` exists, ensure `google-genai` is listed (de-dupe if already present). If not, skip.

- [ ] **Step 8: Commit**

```bash
cd "D:/Repo/Aria Appeal"
git add .gitignore backend/requirements.txt 2>/dev/null
git commit -m "chore: video prereqs — gitignore media, track google-genai dep"
```
(Note: the empty `static/video/*` dirs are not committed because they're now gitignored; that's fine — later code creates them with `os.makedirs(..., exist_ok=True)`.)

---

## Task 2: Provider config on SystemSettings

**Files:**
- Modify: `backend/app/core/system_config.py`
- Test: `backend/tests/test_video_config.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_video_config.py`:
```python
from app.core.system_config import SystemSettings


def test_video_settings_defaults():
    s = SystemSettings()
    assert s.video_provider == "gemini"
    assert s.gemini_api_key == ""
    assert s.veo_model == "veo-3.0-generate-001"


def test_video_settings_roundtrip_json():
    s = SystemSettings(gemini_api_key="abc123", video_provider="gemini")
    dumped = s.model_dump_json()
    restored = SystemSettings.model_validate_json(dumped)
    assert restored.gemini_api_key == "abc123"
    assert restored.video_provider == "gemini"
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/test_video_config.py -v
```
Expected: FAIL — `AttributeError`/validation error (fields `video_provider`, `gemini_api_key`, `veo_model` don't exist yet).

- [ ] **Step 3: Add the fields to SystemSettings**

In `backend/app/core/system_config.py`, inside the `SystemSettings` class, add these fields after the existing `tts_model` field (line ~32):
```python
    video_provider: Literal["gemini", "local"] = Field(
        "gemini",
        description="Generated-video backend: 'gemini' (Veo via Gemini API) or 'local' (future on-prem)."
    )
    gemini_api_key: str = Field(
        "",
        description="Google Gemini API key for Veo video generation."
    )
    veo_model: str = Field(
        "veo-3.0-generate-001",
        description="Veo model id used when video_provider is 'gemini'."
    )
```

- [ ] **Step 4: Mirror the env-var fallback for the Gemini key**

In `ConfigManager.load_config` (in the same file), after the existing `anthropic_api_key` env fallback block (around line 58-61), add an analogous block:
```python
        if not self._settings.gemini_api_key:
            env_gemini = os.environ.get("GEMINI_API_KEY", "")
            if env_gemini:
                self._settings = self._settings.model_copy(update={"gemini_api_key": env_gemini})
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/test_video_config.py -v
```
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
cd "D:/Repo/Aria Appeal"
git add backend/app/core/system_config.py backend/tests/test_video_config.py
git commit -m "feat: add Gemini/Veo video provider settings to SystemSettings"
```

---

## Task 3: VideoClip model

**Files:**
- Create: `backend/app/models/video_clip.py`
- Modify: `backend/app/db/base.py` (register the model for the mapper)
- Test: `backend/tests/test_video_model.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_video_model.py`:
```python
from app.models.video_clip import VideoClip


def test_videoclip_tablename():
    assert VideoClip.__tablename__ == "videoclip"


def test_videoclip_has_expected_columns():
    cols = set(VideoClip.__table__.columns.keys())
    expected = {
        "id", "project_id", "segment_id", "sequence_order", "source_type",
        "prompt", "video_url", "status", "duration_ms",
        "trim_start_ms", "trim_end_ms", "timeline_start_ms", "timeline_end_ms",
        "init_image_path", "created_at",
    }
    missing = expected - cols
    assert not missing, f"missing columns: {missing}"


def test_videoclip_foreign_keys_target_lowercase_tables():
    fks = {fk.target_fullname for fk in VideoClip.__table__.foreign_keys}
    assert "project.id" in fks
    assert "scriptsegment.id" in fks
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/test_video_model.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.video_clip'`.

- [ ] **Step 3: Create the model**

Create `backend/app/models/video_clip.py`:
```python
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, Integer, Enum, DateTime
from app.db.base_class import Base

if TYPE_CHECKING:
    from .project import Project
    from .script_segment import ScriptSegment


class VideoSourceType(str, enum.Enum):
    GENERATED = "generated"
    ASSET = "asset"
    UPLOADED = "uploaded"


class VideoClipStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class VideoClip(Base):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("project.id"))
    # Nullable: Phase 1 sets it (clip mirrors a narration beat); Phase 2 allows
    # null for free-floating clips on an independent track.
    segment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("scriptsegment.id"), nullable=True
    )
    sequence_order: Mapped[int] = mapped_column(Integer)
    source_type: Mapped[VideoSourceType] = mapped_column(
        Enum(VideoSourceType), default=VideoSourceType.GENERATED
    )
    prompt: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[VideoClipStatus] = mapped_column(
        Enum(VideoClipStatus), default=VideoClipStatus.PENDING
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trim_start_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trim_end_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Position on the video track. Derived from the segment in Phase 1; stored now
    # so Phase 2 free placement needs no migration.
    timeline_start_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timeline_end_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    init_image_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    project: Mapped["Project"] = relationship("Project", back_populates="video_clips")
```

- [ ] **Step 4: Register the model in the mapper aggregator**

`backend/app/db/base.py` imports every model so SQLAlchemy's mapper resolves relationships (it's imported by `app/main.py` as `from app.db import base as _`). Open `backend/app/db/base.py` and add, alongside the other `from app.models...` imports:
```python
from app.models.video_clip import VideoClip  # noqa: F401
```

- [ ] **Step 5: Add the reverse relationship + columns on Project**

In `backend/app/models/project.py`:

First, extend the typing import block (top of file) and add `video_clips` to the relationships. Change the `TYPE_CHECKING` block to include the clip type:
```python
if TYPE_CHECKING:
    from .user import User
    from .script_segment import ScriptSegment
    from .video_clip import VideoClip
```
Then add two JSON columns and the relationship to the `Project` class. After the existing `created_at` column line, add:
```python
    video_brief: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    subtitle_style: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
```
And after the existing `segments` relationship line, add:
```python
    video_clips: Mapped[List["VideoClip"]] = relationship("VideoClip", back_populates="project")
```
(`JSON`, `List`, and `Optional` are already imported in `project.py`.)

- [ ] **Step 6: Run the model test to verify it passes**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/test_video_model.py -v
```
Expected: PASS (3 passed).

- [ ] **Step 7: Verify the whole app still imports (mapper integrity)**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -c "from app.main import app; print('app imports ok')"
```
Expected: prints `app imports ok` with no SQLAlchemy mapper errors. If you see "expression 'VideoClip' failed to locate a name", the import in Step 4 is missing or `back_populates` names don't match between `Project.video_clips` and `VideoClip.project`.

- [ ] **Step 8: Commit**

```bash
cd "D:/Repo/Aria Appeal"
git add backend/app/models/video_clip.py backend/app/db/base.py backend/app/models/project.py backend/tests/test_video_model.py
git commit -m "feat: add VideoClip model + project video_brief/subtitle_style columns"
```

---

## Task 4: Pydantic schemas for VideoClip

**Files:**
- Create: `backend/app/schemas/video.py`
- Test: `backend/tests/test_video_schemas.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_video_schemas.py`:
```python
import uuid
from app.schemas.video import VideoClipRead, VideoClipUpdate


def test_videoclipread_minimal():
    vc = VideoClipRead(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        segment_id=None,
        sequence_order=0,
        source_type="generated",
        status="pending",
        prompt=None,
        video_url=None,
        duration_ms=None,
        trim_start_ms=None,
        trim_end_ms=None,
        timeline_start_ms=None,
        timeline_end_ms=None,
    )
    assert vc.source_type == "generated"
    assert vc.status == "pending"


def test_videoclipupdate_is_partial():
    upd = VideoClipUpdate(prompt="new prompt")
    assert upd.prompt == "new prompt"
    assert upd.trim_start_ms is None
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/test_video_schemas.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.schemas.video'`.

- [ ] **Step 3: Create the schemas**

Create `backend/app/schemas/video.py`:
```python
import uuid
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict


class VideoClipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    segment_id: Optional[uuid.UUID] = None
    sequence_order: int
    source_type: Literal["generated", "asset", "uploaded"]
    status: Literal["pending", "generating", "ready", "failed"]
    prompt: Optional[str] = None
    video_url: Optional[str] = None
    duration_ms: Optional[int] = None
    trim_start_ms: Optional[int] = None
    trim_end_ms: Optional[int] = None
    timeline_start_ms: Optional[int] = None
    timeline_end_ms: Optional[int] = None


class VideoClipUpdate(BaseModel):
    """Partial update for editor edits (prompt, trim, ordering)."""
    prompt: Optional[str] = None
    trim_start_ms: Optional[int] = None
    trim_end_ms: Optional[int] = None
    sequence_order: Optional[int] = None


class VideoBrief(BaseModel):
    """Campaign-level visual direction stored in Project.video_brief."""
    style_prompt: Optional[str] = None
    character_sheet: Optional[str] = None
    video_master_url: Optional[str] = None


class SubtitleStyle(BaseModel):
    """Stored in Project.subtitle_style; controls ASS burn-in."""
    enabled: bool = True
    font_size: int = 36
    position: Literal["bottom", "top", "center"] = "bottom"
    color: str = "FFFFFF"
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/test_video_schemas.py -v
```
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
cd "D:/Repo/Aria Appeal"
git add backend/app/schemas/video.py backend/tests/test_video_schemas.py
git commit -m "feat: add VideoClip/VideoBrief/SubtitleStyle Pydantic schemas"
```

---

## Task 5: Database migration

**Files:**
- Create: `backend/alembic/versions/<autogenerated>_add_videoclip_and_project_video_fields.py`

The migration creates the `videoclip` table and adds `video_brief` + `subtitle_style` columns to `project`. Alembic auto-sets `down_revision` to the current head when you generate the revision, so there's no need to hand-pick it.

- [ ] **Step 1: Confirm the current migration head**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m alembic heads
./.venv/Scripts/python.exe -m alembic current
```
Expected: prints a single head revision and the current applied revision. If `current` is behind `heads`, run `./.venv/Scripts/python.exe -m alembic upgrade head` first so you migrate from a clean base.

- [ ] **Step 2: Generate the migration**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m alembic revision -m "add videoclip and project video fields"
```
This creates a new file under `backend/alembic/versions/`. Open it.

- [ ] **Step 3: Fill in the migration body**

Replace the generated `upgrade()` and `downgrade()` functions with the following (keep the auto-generated `revision`/`down_revision` header lines untouched). Add the needed imports at the top (`import sqlalchemy as sa` is usually already present; add `from sqlalchemy.dialects import postgresql`):
```python
def upgrade() -> None:
    op.create_table(
        "videoclip",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("segment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum("GENERATED", "ASSET", "UPLOADED", name="videosourcetype"),
            nullable=False,
        ),
        sa.Column("prompt", sa.String(), nullable=True),
        sa.Column("video_url", sa.String(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PENDING", "GENERATING", "READY", "FAILED", name="videoclipstatus"),
            nullable=False,
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("trim_start_ms", sa.Integer(), nullable=True),
        sa.Column("trim_end_ms", sa.Integer(), nullable=True),
        sa.Column("timeline_start_ms", sa.Integer(), nullable=True),
        sa.Column("timeline_end_ms", sa.Integer(), nullable=True),
        sa.Column("init_image_path", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.ForeignKeyConstraint(["segment_id"], ["scriptsegment.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("project", sa.Column("video_brief", sa.JSON(), nullable=True))
    op.add_column("project", sa.Column("subtitle_style", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("project", "subtitle_style")
    op.drop_column("project", "video_brief")
    op.drop_table("videoclip")
    sa.Enum(name="videoclipstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="videosourcetype").drop(op.get_bind(), checkfirst=True)
```

- [ ] **Step 4: Apply the migration**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m alembic upgrade head
```
Expected: runs without error; logs `Running upgrade ... -> <new rev>`.

- [ ] **Step 5: Verify the table and columns exist**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -c "
import asyncio
from sqlalchemy import text
from app.db.session import SessionLocal
async def main():
    async with SessionLocal() as db:
        r = await db.execute(text(\"select column_name from information_schema.columns where table_name='videoclip' order by column_name\"))
        print('videoclip cols:', [row[0] for row in r])
        r2 = await db.execute(text(\"select column_name from information_schema.columns where table_name='project' and column_name in ('video_brief','subtitle_style')\"))
        print('project new cols:', [row[0] for row in r2])
asyncio.run(main())
"
```
Expected: prints the full `videoclip` column list and `project new cols: ['video_brief', 'subtitle_style']` (order may vary).

- [ ] **Step 6: Verify downgrade then re-upgrade (round-trip safety)**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m alembic downgrade -1
./.venv/Scripts/python.exe -m alembic upgrade head
```
Expected: both complete without error. (This confirms `downgrade()` is correct and the migration is re-runnable.)

- [ ] **Step 7: Commit**

```bash
cd "D:/Repo/Aria Appeal"
git add backend/alembic/versions/
git commit -m "feat: migration for videoclip table + project video fields"
```

---

## Task 6: Full-suite regression check

- [ ] **Step 1: Run the backend test suite**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/ -v
```
Expected: all previously-passing tests still pass, plus the three new test files (`test_video_config.py`, `test_video_model.py`, `test_video_schemas.py`). If a pre-existing test was already failing before this plan (e.g. a DB-dependent test in an offline environment), note it but do not treat it as a regression caused by this work.

- [ ] **Step 2: Final import smoke check**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -c "from app.main import app; print('ok')"
```
Expected: `ok`.

---

## Done criteria for Plan 1

- ffmpeg/ffprobe on PATH; `google-genai` installed and importable.
- `SystemSettings` has `video_provider`, `gemini_api_key`, `veo_model` with env fallback.
- `videoclip` table exists; `project` has `video_brief` + `subtitle_style`.
- New Pydantic schemas import and validate.
- Migration applies, round-trips, and is committed.
- `from app.main import app` succeeds.

**Next:** Plan 2 — Video engine (`VideoProvider` abstraction, ffmpeg normalization, Gemini/asset/upload providers, `video_service`, background generation tasks, and the launcher Settings UI for the Gemini key).
