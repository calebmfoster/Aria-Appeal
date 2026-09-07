# Video Previsualization — Plan 2: Video Engine (Providers + ffmpeg utils)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **PACING RULE — read this:** This plan has external, costly dependencies (real ffmpeg, real paid Veo calls). After each task, STOP at its 🔍 MANUAL CHECKPOINT and wait for the human to run the manual test plan (`2026-06-27-video-previs-02-engine-MANUAL-TESTS.md`) and give an explicit GO before the next task. Do not chain tasks past a checkpoint.

**Goal:** Build the provider-agnostic video engine: a `VideoProvider` interface with Asset/Gemini-Veo/Local implementations, plus the ffmpeg utilities (normalize, probe, extract-last-frame) they rely on, and the launcher UI for the Gemini key. No DB orchestration or HTTP endpoints yet (that's Plan 3).

**Architecture:** Pure service layer under `backend/app/services/video/`. Providers return a raw clip path + duration; the shared ffmpeg normalization is a separate utility applied later by `video_service` (Plan 3). The Gemini provider wraps the synchronous `google-genai` SDK in `asyncer.asyncify` to satisfy the async interface, matching how `audio.py` bridges sync TTS work.

**Tech Stack:** Python 3.12, `google-genai` 2.10.0 (Veo), ffmpeg/ffprobe (CLI), asyncer, pytest.

**Source spec:** `docs/superpowers/specs/2026-06-26-video-previsualization-design.md`
**Builds on:** Plan 1 (config fields `gemini_api_key`/`veo_model`/`video_provider`, static dirs).

---

## Pre-flight

- [ ] **Step 0: Confirm branch + base**

```bash
cd "D:/Repo/Aria Appeal"
git checkout feat/video-previs
git log --oneline -1
```
Expected: on `feat/video-previs`, HEAD is the migration commit (`9f84d56` or later).

- [ ] **Step 1: Create the package dir**

```bash
cd "D:/Repo/Aria Appeal/backend"
mkdir -p app/services/video
touch app/services/video/__init__.py
```

---

## Task 1: Provider contracts (dataclasses + ABC)

**Files:**
- Create: `backend/app/services/video/base.py`
- Test: `backend/tests/test_video_provider_base.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_video_provider_base.py`:
```python
import inspect
import pytest
from app.services.video.base import VideoGenRequest, VideoGenResult, VideoProvider


def test_request_defaults():
    r = VideoGenRequest(prompt="a cat")
    assert r.prompt == "a cat"
    assert r.aspect_ratio == "16:9"
    assert r.duration_s == 8.0
    assert r.init_image_path is None


def test_result_fields():
    res = VideoGenResult(video_path="/tmp/x.mp4", duration_ms=8000)
    assert res.video_path == "/tmp/x.mp4"
    assert res.duration_ms == 8000


def test_provider_is_abstract():
    assert inspect.isabstract(VideoProvider)
    with pytest.raises(TypeError):
        VideoProvider()
```

- [ ] **Step 2: Run the test; confirm FAIL**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/test_video_provider_base.py -v
```
Expected: FAIL — `ModuleNotFoundError: app.services.video.base`.

- [ ] **Step 3: Implement**

Create `backend/app/services/video/base.py`:
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class VideoGenRequest:
    prompt: str
    style_prompt: Optional[str] = None
    character_sheet: Optional[str] = None
    init_image_path: Optional[str] = None
    duration_s: float = 8.0
    aspect_ratio: str = "16:9"


@dataclass
class VideoGenResult:
    video_path: str
    duration_ms: Optional[int] = None


class VideoProvider(ABC):
    """Produces a raw video clip from a request. Normalization happens downstream."""

    name: str = "base"

    @abstractmethod
    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        ...
```

- [ ] **Step 4: Run the test; confirm PASS (3 passed)**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/test_video_provider_base.py -v
```

- [ ] **Step 5: Commit**

```bash
cd "D:/Repo/Aria Appeal"
git add backend/app/services/video/__init__.py backend/app/services/video/base.py backend/tests/test_video_provider_base.py
git commit -m "feat: VideoProvider interface + request/result dataclasses

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] 🔍 **MANUAL CHECKPOINT 1** — Pure code, no external deps. Human confirms the 3 tests pass. GO/NO-GO. (See manual test plan, Checkpoint 1.)

---

## Task 2: ffmpeg utilities

**Files:**
- Create: `backend/app/services/video/ffmpeg_utils.py`
- Test: `backend/tests/test_ffmpeg_utils.py`

These shell out to ffmpeg/ffprobe. Because ffmpeg may not be on a given shell's PATH (it was installed in Plan 1 but needs a fresh shell), the resolver checks an env var `FFMPEG_BINARY`/`FFPROBE_BINARY`, then `shutil.which`. Tests that need a working ffmpeg **skip** (not fail) when it can't be resolved — the real validation is the manual checkpoint.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_ffmpeg_utils.py`:
```python
import os
import subprocess
import pytest
from app.services.video import ffmpeg_utils


def _ffmpeg_available():
    try:
        return ffmpeg_utils.resolve_ffmpeg() is not None and ffmpeg_utils.resolve_ffprobe() is not None
    except Exception:
        return False


requires_ffmpeg = pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg/ffprobe not resolvable in this shell")


def test_resolvers_return_string_or_none():
    # Should not raise; returns a path string or None
    assert ffmpeg_utils.resolve_ffmpeg() is None or isinstance(ffmpeg_utils.resolve_ffmpeg(), str)
    assert ffmpeg_utils.resolve_ffprobe() is None or isinstance(ffmpeg_utils.resolve_ffprobe(), str)


@requires_ffmpeg
def test_normalize_and_probe(tmp_path):
    ff = ffmpeg_utils.resolve_ffmpeg()
    src = str(tmp_path / "src.mp4")
    # Synthesize a 2s 320x240 test clip WITH audio at 15fps
    subprocess.run(
        [ff, "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=15:duration=2",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
         "-shortest", "-pix_fmt", "yuv420p", src],
        check=True, capture_output=True,
    )
    dst = str(tmp_path / "out.mp4")
    out = ffmpeg_utils.normalize_clip(src, dst)
    assert out == dst and os.path.exists(dst)

    info = ffmpeg_utils.probe_stream_info(dst)
    assert info["width"] == 1920 and info["height"] == 1080
    assert abs(info["fps"] - 30.0) < 0.5
    assert info["has_audio"] is False  # audio stripped

    dur = ffmpeg_utils.probe_duration_ms(dst)
    assert 1500 <= dur <= 2500


@requires_ffmpeg
def test_extract_last_frame(tmp_path):
    ff = ffmpeg_utils.resolve_ffmpeg()
    src = str(tmp_path / "src.mp4")
    subprocess.run(
        [ff, "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=15:duration=2",
         "-pix_fmt", "yuv420p", src],
        check=True, capture_output=True,
    )
    out_png = str(tmp_path / "last.png")
    res = ffmpeg_utils.extract_last_frame(src, out_png)
    assert res == out_png and os.path.exists(out_png) and os.path.getsize(out_png) > 0
```

- [ ] **Step 2: Run the test; confirm it FAILS**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/test_ffmpeg_utils.py -v
```
Expected: FAIL — `ModuleNotFoundError: app.services.video.ffmpeg_utils` (the `@requires_ffmpeg` tests may show as skipped only after the module exists).

- [ ] **Step 3: Implement**

Create `backend/app/services/video/ffmpeg_utils.py`:
```python
import os
import json
import shutil
import subprocess
from typing import Optional

# Normalization target — every clip becomes this uniform format so concat is trivial.
TARGET_W = 1920
TARGET_H = 1080
TARGET_FPS = 30


def resolve_ffmpeg() -> Optional[str]:
    return os.environ.get("FFMPEG_BINARY") or shutil.which("ffmpeg")


def resolve_ffprobe() -> Optional[str]:
    return os.environ.get("FFPROBE_BINARY") or shutil.which("ffprobe")


def _require(bin_path: Optional[str], name: str) -> str:
    if not bin_path:
        raise RuntimeError(
            f"{name} not found. Install ffmpeg and ensure it is on PATH, or set the "
            f"{name.upper()}_BINARY environment variable."
        )
    return bin_path


def normalize_clip(src_path: str, dst_path: str,
                   width: int = TARGET_W, height: int = TARGET_H, fps: int = TARGET_FPS) -> str:
    """Transcode any clip to uniform H.264, fixed resolution (letterboxed), fps, NO audio."""
    ff = _require(resolve_ffmpeg(), "ffmpeg")
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,fps={fps}"
    )
    os.makedirs(os.path.dirname(dst_path) or ".", exist_ok=True)
    subprocess.run(
        [ff, "-y", "-i", src_path, "-vf", vf,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", dst_path],
        check=True, capture_output=True,
    )
    return dst_path


def probe_duration_ms(path: str) -> Optional[int]:
    fp = resolve_ffprobe()
    if not fp:
        return None
    try:
        out = subprocess.run(
            [fp, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        return round(float(out) * 1000)
    except (subprocess.CalledProcessError, ValueError):
        # Non-video / unreadable file — duration unknown, not fatal.
        return None


def probe_stream_info(path: str) -> dict:
    """Return {width, height, fps, has_audio} via ffprobe JSON."""
    fp = _require(resolve_ffprobe(), "ffprobe")
    out = subprocess.run(
        [fp, "-v", "error", "-show_streams", "-of", "json", path],
        check=True, capture_output=True, text=True,
    ).stdout
    data = json.loads(out)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    fps = 0.0
    rate = video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1"
    try:
        num, den = rate.split("/")
        fps = float(num) / float(den) if float(den) else 0.0
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    return {
        "width": int(video.get("width", 0)),
        "height": int(video.get("height", 0)),
        "fps": fps,
        "has_audio": has_audio,
    }


def extract_last_frame(video_path: str, out_image_path: str) -> str:
    """Grab the final frame as a PNG (for tail-frame chaining)."""
    ff = _require(resolve_ffmpeg(), "ffmpeg")
    os.makedirs(os.path.dirname(out_image_path) or ".", exist_ok=True)
    # -sseof seeks relative to end of file; -update 1 writes a single image.
    subprocess.run(
        [ff, "-y", "-sseof", "-0.1", "-i", video_path,
         "-update", "1", "-frames:v", "1", out_image_path],
        check=True, capture_output=True,
    )
    return out_image_path
```

- [ ] **Step 4: Run the test**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/test_ffmpeg_utils.py -v
```
Expected: `test_resolvers_return_string_or_none` PASSES. The two `@requires_ffmpeg` tests PASS if ffmpeg is on this shell's PATH, otherwise SKIP. Either outcome is acceptable for the automated step — the manual checkpoint validates them for real.

- [ ] **Step 5: Commit**

```bash
cd "D:/Repo/Aria Appeal"
git add backend/app/services/video/ffmpeg_utils.py backend/tests/test_ffmpeg_utils.py
git commit -m "feat: ffmpeg utils — normalize, probe, extract last frame

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] 🔍 **MANUAL CHECKPOINT 2 — STOP.** Human runs ffmpeg tests in a fresh shell (where ffmpeg resolves) and eyeballs a normalized clip. This is the first real ffmpeg validation. GO/NO-GO. (Manual test plan, Checkpoint 2.)

---

## Task 3: AssetVideoProvider

**Files:**
- Create: `backend/app/services/video/asset_provider.py`
- Test: `backend/tests/test_asset_provider.py`

The asset provider resolves a pre-placed file under `static/video/assets/`. The request's `prompt` carries the asset filename (the orchestration layer in Plan 3 sets this). It returns the raw path + probed duration. It does NOT normalize (that's Plan 3's `video_service`).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_asset_provider.py` (sync tests driving the async method via
`asyncio.run`, so no async-pytest plugin is needed):
```python
import asyncio
import pytest
from app.services.video.asset_provider import AssetVideoProvider
from app.services.video.base import VideoGenRequest


def test_resolves_existing_asset(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    f = assets / "clip1.mp4"
    f.write_bytes(b"not a real mp4 but a file")

    p = AssetVideoProvider(assets_dir=str(assets))
    res = asyncio.run(p.generate(VideoGenRequest(prompt="clip1.mp4")))
    assert res.video_path == str(f)


def test_missing_asset_raises(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    p = AssetVideoProvider(assets_dir=str(assets))
    with pytest.raises(FileNotFoundError):
        asyncio.run(p.generate(VideoGenRequest(prompt="nope.mp4")))
```

- [ ] **Step 2: Run the test; confirm it FAILS**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/test_asset_provider.py -v
```
Expected: FAIL — `ModuleNotFoundError: app.services.video.asset_provider`.

- [ ] **Step 3: Implement**

Create `backend/app/services/video/asset_provider.py`:
```python
import os
from app.services.video.base import VideoProvider, VideoGenRequest, VideoGenResult
from app.services.video import ffmpeg_utils


class AssetVideoProvider(VideoProvider):
    """Returns a pre-placed clip from the assets dir. `req.prompt` is the filename."""

    name = "asset"

    def __init__(self, assets_dir: str):
        self.assets_dir = assets_dir

    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        filename = os.path.basename(req.prompt or "")
        path = os.path.join(self.assets_dir, filename)
        if not filename or not os.path.exists(path):
            raise FileNotFoundError(f"Asset clip not found: {path}")
        return VideoGenResult(video_path=path, duration_ms=ffmpeg_utils.probe_duration_ms(path))
```

- [ ] **Step 4: Run the test; confirm PASS (2 passed)**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/test_asset_provider.py -v
```

- [ ] **Step 5: Commit**

```bash
cd "D:/Repo/Aria Appeal"
git add backend/app/services/video/asset_provider.py backend/tests/test_asset_provider.py
git commit -m "feat: AssetVideoProvider — resolve pre-placed clips

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] 🔍 **MANUAL CHECKPOINT 3** — Human drops a real mp4 into `backend/static/video/assets/` and confirms the provider resolves it. GO/NO-GO. (Manual test plan, Checkpoint 3.)

---

## Task 4: GeminiVeoProvider

**Files:**
- Create: `backend/app/services/video/gemini_provider.py`
- Test: `backend/tests/test_gemini_provider.py`

Wraps the synchronous `google-genai` Veo flow in `asyncer.asyncify`. The unit test injects a fake client so **no real API call or cost** is incurred; the real call is the manual checkpoint.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_gemini_provider.py`:
```python
import os
import asyncio
import types as pytypes
import pytest
from app.services.video.gemini_provider import GeminiVeoProvider
from app.services.video.base import VideoGenRequest


class _FakeVideo:
    pass


class _FakeOp:
    def __init__(self):
        self.done = False
        self.error = None
        self.response = pytypes.SimpleNamespace(
            generated_videos=[pytypes.SimpleNamespace(video=_FakeVideo())]
        )


class _FakeModels:
    def __init__(self, op):
        self._op = op
        self.last_kwargs = None

    def generate_videos(self, **kwargs):
        self.last_kwargs = kwargs
        return self._op


class _FakeOperations:
    def __init__(self, op):
        self._op = op

    def get(self, op):
        op.done = True  # finish on first poll
        return op


class _FakeFiles:
    def download(self, *, file):
        return b"FAKE_MP4_BYTES"


class _FakeClient:
    def __init__(self, op):
        self.models = _FakeModels(op)
        self.operations = _FakeOperations(op)
        self.files = _FakeFiles()


def test_generate_writes_file_and_composes_prompt(tmp_path, monkeypatch):
    op = _FakeOp()
    fake_client = _FakeClient(op)

    p = GeminiVeoProvider(
        api_key="test-key", model="veo-3.0-generate-001",
        out_dir=str(tmp_path), poll_interval_s=0, timeout_s=10,
    )
    monkeypatch.setattr(p, "_make_client", lambda: fake_client)

    req = VideoGenRequest(prompt="a volunteer", style_prompt="golden hour", character_sheet="MARIA: 60s")
    res = asyncio.run(p.generate(req))

    assert os.path.exists(res.video_path)
    with open(res.video_path, "rb") as f:
        assert f.read() == b"FAKE_MP4_BYTES"
    # style + character sheet folded into the prompt sent to Veo
    sent = fake_client.models.last_kwargs["prompt"]
    assert "a volunteer" in sent and "golden hour" in sent and "MARIA" in sent
    assert fake_client.models.last_kwargs["model"] == "veo-3.0-generate-001"
```

- [ ] **Step 2: Run the test; confirm it FAILS**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/test_gemini_provider.py -v
```
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

Create `backend/app/services/video/gemini_provider.py`:
```python
import os
import time
import uuid
import asyncer
from typing import Optional
from app.services.video.base import VideoProvider, VideoGenRequest, VideoGenResult
from app.services.video import ffmpeg_utils


class GeminiVeoProvider(VideoProvider):
    """Generates a clip via Google Veo (Gemini API). Visuals only — audio is
    stripped later during normalization, so we do not set generate_audio."""

    name = "gemini"

    def __init__(self, api_key: str, model: str, out_dir: str,
                 poll_interval_s: float = 8.0, timeout_s: float = 300.0):
        self.api_key = api_key
        self.model = model
        self.out_dir = out_dir
        self.poll_interval_s = poll_interval_s
        self.timeout_s = timeout_s

    def _make_client(self):
        from google import genai
        return genai.Client(api_key=self.api_key)

    @staticmethod
    def _compose_prompt(req: VideoGenRequest) -> str:
        parts = [req.prompt or ""]
        if req.style_prompt:
            parts.append(f"Style: {req.style_prompt}")
        if req.character_sheet:
            parts.append(f"Consistent subjects: {req.character_sheet}")
        return "\n".join(p for p in parts if p)

    def _generate_sync(self, req: VideoGenRequest) -> VideoGenResult:
        from google.genai import types

        if not self.api_key:
            raise RuntimeError(
                "Gemini API key is not configured. Set it in the launcher Settings "
                "panel or the GEMINI_API_KEY environment variable."
            )
        client = self._make_client()

        image = None
        if req.init_image_path and os.path.exists(req.init_image_path):
            with open(req.init_image_path, "rb") as f:
                data = f.read()
            mime = "image/png" if req.init_image_path.lower().endswith(".png") else "image/jpeg"
            image = types.Image(image_bytes=data, mime_type=mime)

        config = types.GenerateVideosConfig(
            number_of_videos=1,
            aspect_ratio=req.aspect_ratio,
            duration_seconds=int(req.duration_s),
        )
        op = client.models.generate_videos(
            model=self.model,
            prompt=self._compose_prompt(req),
            image=image,
            config=config,
        )

        waited = 0.0
        while not op.done:
            time.sleep(self.poll_interval_s)
            waited += self.poll_interval_s
            if waited > self.timeout_s:
                raise TimeoutError(f"Veo generation timed out after {self.timeout_s}s")
            op = client.operations.get(op)

        if getattr(op, "error", None):
            raise RuntimeError(f"Veo generation failed: {op.error}")

        video = op.response.generated_videos[0].video
        data = client.files.download(file=video)
        os.makedirs(self.out_dir, exist_ok=True)
        out_path = os.path.join(self.out_dir, f"veo_{uuid.uuid4().hex}.mp4")
        with open(out_path, "wb") as f:
            f.write(data)

        return VideoGenResult(video_path=out_path, duration_ms=ffmpeg_utils.probe_duration_ms(out_path))

    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        return await asyncer.asyncify(self._generate_sync)(req)
```

- [ ] **Step 4: Run the test; confirm PASS (1 passed)**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/test_gemini_provider.py -v
```

- [ ] **Step 5: Commit**

```bash
cd "D:/Repo/Aria Appeal"
git add backend/app/services/video/gemini_provider.py backend/tests/test_gemini_provider.py
git commit -m "feat: GeminiVeoProvider — Veo generation via google-genai (mocked in tests)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] 🔍 **MANUAL CHECKPOINT 4 — STOP. COSTS MONEY.** Only after the launcher key UI (Task 6) is also done, the human makes ONE real Veo call via the manual script and inspects the resulting mp4. Do not loop or batch. GO/NO-GO. (Manual test plan, Checkpoint 4 — run it after Task 6.)

---

## Task 5: LocalVideoProvider stub + provider factory

**Files:**
- Create: `backend/app/services/video/local_provider.py`
- Create: `backend/app/services/video/factory.py`
- Test: `backend/tests/test_video_factory.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_video_factory.py`:
```python
import asyncio
import pytest
from app.services.video.factory import get_video_provider
from app.services.video.asset_provider import AssetVideoProvider
from app.services.video.gemini_provider import GeminiVeoProvider
from app.services.video.local_provider import LocalVideoProvider
from app.services.video.base import VideoGenRequest


def test_asset_source_returns_asset_provider():
    p = get_video_provider("asset")
    assert isinstance(p, AssetVideoProvider)


def test_uploaded_source_returns_asset_provider():
    # uploads are resolved the same way as assets (pre-existing files)
    p = get_video_provider("uploaded")
    assert isinstance(p, AssetVideoProvider)


def test_generated_gemini_returns_gemini(monkeypatch):
    from app.core import system_config
    s = system_config.config_manager.get_settings().model_copy(
        update={"video_provider": "gemini", "gemini_api_key": "k", "veo_model": "veo-3.0-generate-001"}
    )
    monkeypatch.setattr(system_config.config_manager, "get_settings", lambda: s)
    p = get_video_provider("generated")
    assert isinstance(p, GeminiVeoProvider)


def test_generated_local_returns_local(monkeypatch):
    from app.core import system_config
    s = system_config.config_manager.get_settings().model_copy(update={"video_provider": "local"})
    monkeypatch.setattr(system_config.config_manager, "get_settings", lambda: s)
    p = get_video_provider("generated")
    assert isinstance(p, LocalVideoProvider)


def test_local_provider_not_implemented():
    with pytest.raises(NotImplementedError):
        asyncio.run(LocalVideoProvider().generate(VideoGenRequest(prompt="x")))
```

- [ ] **Step 2: Run the test; confirm it FAILS**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/test_video_factory.py -v
```
Expected: FAIL — modules missing.

- [ ] **Step 3: Implement the stub**

Create `backend/app/services/video/local_provider.py`:
```python
from app.services.video.base import VideoProvider, VideoGenRequest, VideoGenResult


class LocalVideoProvider(VideoProvider):
    """Placeholder for future on-prem generation (company hardware)."""

    name = "local"

    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        raise NotImplementedError(
            "Local video generation is not implemented yet. Use the Gemini provider."
        )
```

- [ ] **Step 4: Implement the factory**

Create `backend/app/services/video/factory.py`:
```python
import os
from app.core.config import settings as app_settings
from app.core.system_config import config_manager
from app.services.video.base import VideoProvider
from app.services.video.asset_provider import AssetVideoProvider
from app.services.video.gemini_provider import GeminiVeoProvider
from app.services.video.local_provider import LocalVideoProvider


def _static_video_dir(sub: str) -> str:
    base = app_settings.STATIC_AUDIO_DIR
    root = os.path.dirname(base) if base else os.path.join(os.getcwd(), "static")
    return os.path.join(root, "video", sub)


def get_video_provider(source_type: str) -> VideoProvider:
    """Resolve a provider for a clip's source_type.
    - 'asset' / 'uploaded' -> AssetVideoProvider (pre-existing files on disk)
    - 'generated' -> the configured generated backend (gemini | local)
    """
    if source_type in ("asset", "uploaded"):
        sub = "assets" if source_type == "asset" else "uploads"
        return AssetVideoProvider(assets_dir=_static_video_dir(sub))

    s = config_manager.get_settings()
    if s.video_provider == "local":
        return LocalVideoProvider()
    return GeminiVeoProvider(
        api_key=s.gemini_api_key,
        model=s.veo_model,
        out_dir=_static_video_dir("clips"),
    )
```

- [ ] **Step 5: Run the test; confirm PASS (5 passed)**

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/test_video_factory.py -v
```

- [ ] **Step 6: Commit**

```bash
cd "D:/Repo/Aria Appeal"
git add backend/app/services/video/local_provider.py backend/app/services/video/factory.py backend/tests/test_video_factory.py
git commit -m "feat: LocalVideoProvider stub + provider factory

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] 🔍 **MANUAL CHECKPOINT 5** — Pure code. Human confirms 5 tests pass. GO/NO-GO. (Manual test plan, Checkpoint 5.)

---

## Task 6: Launcher Settings UI for the Gemini key

**Files:**
- Modify: `launcher.py`

`launcher.py` is a tkinter GUI that already has a Settings panel with a masked Anthropic key entry, a Claude model picker, and writes to `config.json` via `_save_config`. Add: a masked **Gemini API key** entry, a **Veo model** entry, and a **video provider** toggle (gemini/local), persisting keys `gemini_api_key`, `veo_model`, `video_provider`. This task is UI — verified manually (no unit test).

- [ ] **Step 1: Read the existing Settings panel code**

Open `launcher.py` and locate: `DEFAULT_CONFIG`, the Settings panel builder (where the Anthropic key `Entry` with `show="*"` and the Claude model `OptionMenu` are created), and `_save_settings`. Note the exact widget/variable patterns used.

- [ ] **Step 2: Add the defaults**

In `DEFAULT_CONFIG`, add:
```python
    "video_provider": "gemini",
    "gemini_api_key": "",
    "veo_model": "veo-3.0-generate-001",
```

- [ ] **Step 3: Add the widgets**

In the Settings panel builder, mirroring the existing Anthropic key row, add three rows bound to new tk variables (`self._gemini_key_var`, `self._veo_model_var`, `self._video_provider_var`):
- a masked `Entry` (`show="*"`) for the Gemini API key, initialized from `self._cfg.get("gemini_api_key", "")`;
- an `Entry` for the Veo model, initialized from `self._cfg.get("veo_model", "veo-3.0-generate-001")`;
- an `OptionMenu` for video provider with values `["gemini", "local"]`, initialized from `self._cfg.get("video_provider", "gemini")`.
Use the same styling constants (BG/FG/fonts) as the surrounding rows.

- [ ] **Step 4: Persist on save**

In `_save_settings`, add the three values to the dict written to config:
```python
        self._cfg["gemini_api_key"] = self._gemini_key_var.get().strip()
        self._cfg["veo_model"] = self._veo_model_var.get().strip() or "veo-3.0-generate-001"
        self._cfg["video_provider"] = self._video_provider_var.get()
```
(Match the exact persistence mechanism the existing keys use — e.g. `_save_config(self._cfg)`.)

- [ ] **Step 5: Smoke-check the launcher imports/parses**

```bash
cd "D:/Repo/Aria Appeal"
python -c "import ast; ast.parse(open('launcher.py', encoding='utf-8').read()); print('launcher.py parses ok')"
```
Expected: `launcher.py parses ok`.

- [ ] **Step 6: Commit**

```bash
cd "D:/Repo/Aria Appeal"
git add launcher.py
git commit -m "feat: launcher Settings — Gemini API key, Veo model, video provider toggle

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] 🔍 **MANUAL CHECKPOINT 6 — STOP.** Human launches the GUI, enters the real Gemini key, saves, and confirms `config.json` has `gemini_api_key`. THEN run Checkpoint 4 (the real Veo call). GO/NO-GO. (Manual test plan, Checkpoint 6.)

---

## Done criteria for Plan 2

- `VideoProvider` interface + Asset/Gemini/Local providers + factory, all unit-tested (no real API cost in CI).
- ffmpeg utilities (normalize/probe/extract-last-frame) implemented and manually validated against real ffmpeg.
- Launcher persists the Gemini key + Veo model + provider toggle.
- One real Veo clip generated and inspected (Checkpoint 4).

**Next:** Plan 3 — generation (art-direction LLM pass + `video_service` orchestration: create clips, run generation in background with tail-frame chaining, normalize on ingest, status polling) and the upload endpoint.
