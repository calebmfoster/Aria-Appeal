# Video Previsualization — Plan 3: Orchestration (Art Direction + Clip Lifecycle)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.
>
> **PACING RULE:** Unlike Plan 2, most tasks here are pure code with unit tests and need no human
> gate — run them straight through and show test output. There are only **two** MANUAL CHECKPOINTS,
> both involving real media files. Do not invent extra stops.

**Goal:** Everything between "a campaign exists" and "an ordered set of ready clips exists," without
depending on any paid video API. Art-direction LLM pass, `VideoClip` provisioning, file ingest +
normalization, upload/attach endpoints, provider-agnostic generation, and the editor's CRUD surface.

**Source spec:** `docs/superpowers/specs/2026-06-26-video-previsualization-design.md`
**Builds on:** Plan 1 (model/migration/schemas), Plan 2 (providers, factory, ffmpeg_utils).

---

## Demo posture — why this plan is asset-first

A client demo to the **CTO, CAO and CIO is scheduled for the week of 2026-09-14**. That audience
evaluates architecture and vendor risk, and has said it may want a different video provider entirely.
Two consequences shape every task below:

1. **The asset/upload path is the primary path, not a fallback.** Clips hand-made in Google Flow (or
   any tool) are downloaded, uploaded into a campaign, and flow through the identical pipeline. Veo
   generation is one config switch that changes nothing downstream. This is both the demo-safe route
   (no live API call in front of the room, no billing dependency) and the honest architecture story.
2. **Nothing downstream of `VideoProvider` may reference a provider.** Assembly (Plan 4), the editor
   (Plan 5) and export read `VideoClip.video_url` only. If any task here needs to branch on provider,
   the abstraction is wrong — stop and fix the seam instead.

Corollary for testing: **every test in this plan must pass with no API key configured.**

---

## Pre-flight

- [ ] **Step 0: Confirm branch + base**

```bash
cd "D:/Repo/Aria Appeal" && git checkout feat/video-previs && git log --oneline -1
```
Expected: on `feat/video-previs`, HEAD is `b11e80e` (manual-test-plan sync) or later.

- [ ] **Step 1: Confirm the Plan 2 surface is intact**

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe -m pytest tests/test_video_provider_base.py tests/test_ffmpeg_utils.py tests/test_asset_provider.py tests/test_gemini_provider.py tests/test_video_factory.py -q
```
Expected: 31 passed. (The wider suite has 5 known-stale failures — see `Open_Issues.md`. Ignore them.)

---

## Task 1: Art-direction LLM pass

**Files:** create `backend/app/services/video/art_direction.py`, test `backend/tests/test_art_direction.py`

A second LLM call, separate from script generation so visual direction regenerates independently.
Reuses the existing `claude`/`local` toggle in `app/services/llm.py` — read `_build_prompt_content`,
`_parse_sentences` and `_generate_with_claude` (llm.py:47/73/108) and mirror those patterns rather
than inventing a new client path.

Contract:
```python
@dataclass
class ArtDirection:
    style_prompt: str
    character_sheet: str
    shot_prompts: list[str]   # one per segment, in order

def build_art_direction(segments: list[str], context: dict) -> ArtDirection: ...
```

- [ ] **Step 1:** Write `tests/test_art_direction.py` first. Mock the LLM call — no network. Cover:
  parses a well-formed response into the dataclass; pads/truncates `shot_prompts` to exactly
  `len(segments)` when the model returns the wrong count (it will); raises a clear error on
  unparseable output. Assert the prompt sent asks for a *visual bible + one shot per segment*.
- [ ] **Step 2:** Run; confirm FAIL (module missing).
- [ ] **Step 3:** Implement. Length-mismatch handling is the important part — a short list must not
  silently leave trailing segments prompt-less.
- [ ] **Step 4:** Run; confirm PASS.
- [ ] **Step 5:** Commit `feat: art-direction LLM pass — visual bible + per-segment shot prompts`.

---

## Task 2: Clip provisioning

**Files:** create `backend/app/services/video/video_service.py`, test `backend/tests/test_video_service_provision.py`

```python
async def provision_clips(db, project_id, art: ArtDirection | None = None) -> list[VideoClip]: ...
```
Creates one `VideoClip` per segment: `status=PENDING`, `source_type=GENERATED`, `sequence_order` and
`segment_id` mirrored from the segment, `prompt` from `art.shot_prompts[i]` when art is supplied.
Writes `style_prompt`/`character_sheet` to `Project.video_brief`.

**Provisioning spends nothing** — it only creates rows. Guard this with a test.

- [ ] **Step 1:** Write the test. Cover: one clip per segment in the right order; `PENDING` status;
  `video_brief` populated; **calling it twice does not duplicate clips** (idempotent per project);
  works with `art=None` (clips exist with empty prompts, for the pure-upload path).
- [ ] **Step 2:** Run; confirm FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run; confirm PASS.
- [ ] **Step 5:** Commit `feat: provision one pending VideoClip per segment`.

---

## Task 3: Ingest + normalization

**Files:** extend `video_service.py`, test `backend/tests/test_video_ingest.py`

```python
async def ingest_clip_file(db, clip, src_path, source_type) -> VideoClip: ...
```
The single choke point every clip passes through regardless of origin: normalize via
`ffmpeg_utils.normalize_clip` into `static/video/clips/`, probe duration, set `video_url`
(`/static/video/clips/<name>.mp4`), `duration_ms`, `status=READY`. On ffmpeg failure set
`status=FAILED` and leave a usable error — a bad upload must not 500 the request.

- [ ] **Step 1:** Write the test. Synthesize a real input clip with ffmpeg (as
  `tests/test_ffmpeg_utils.py` does) and mark it `@requires_ffmpeg`; skip cleanly without ffmpeg.
  Cover: output is 1920x1080/30fps/no-audio; `video_url` is a `/static/` URL not a filesystem path;
  a corrupt input yields `status=FAILED` rather than an exception escaping.
- [ ] **Step 2:** Run; confirm FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run; confirm PASS.
- [ ] **Step 5:** Commit `feat: normalize-on-ingest choke point for all clip sources`.

---

## Task 4: Upload + attach-asset endpoints

**Files:** create `backend/app/api/routes/video.py`, register in `app/main.py`, test `backend/tests/test_video_routes_upload.py`

Mirror the auth/session patterns in `app/api/routes/projects.py` (router at projects.py:146) and the
existing voice-upload route for multipart handling.

- `POST /api/v1/projects/{id}/video/clips/{clip_id}/upload` — multipart mp4, then `ingest_clip_file(..., UPLOADED)`
- `POST /api/v1/projects/{id}/video/clips/{clip_id}/asset` — `{filename}` from `static/video/assets/`, then `ingest_clip_file(..., ASSET)`

Validate content type and cap upload size. Reject a filename that escapes the assets dir —
`AssetVideoProvider` already basenames, but the route should not rely on that alone.

- [ ] **Step 1:** Write the test (FastAPI `TestClient`). Cover: successful upload sets the clip
  `READY` with a `video_url`; non-video upload is rejected; traversal filename is rejected; a clip
  belonging to another user's project 404s.
- [ ] **Step 2:** Run; confirm FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run; confirm PASS.
- [ ] **Step 5:** Commit `feat: clip upload + asset-attach endpoints`.

- [ ] **MANUAL CHECKPOINT A — real Flow clip, end to end.** Human generates a clip in Google Flow
  (free daily credits), downloads the mp4, and uploads it to a real campaign clip through the running
  backend. Confirm: it normalizes, appears under `static/video/clips/`, plays in a browser at its
  `video_url`, and the row reads `READY` with a sane `duration_ms`. **This is the demo's critical
  path — if it works, the demo is viable without any paid API.** GO/NO-GO.

---

## Task 5: Provider-agnostic generation

**Files:** extend `video_service.py`, test `backend/tests/test_video_generate.py`

```python
async def generate_clip(db, clip) -> VideoClip: ...
async def generate_all_for_project(db, project_id) -> None: ...
```
`generate_clip` resolves via `get_video_provider(clip.source_type)`, sets `GENERATING`, calls
`provider.generate(...)`, then hands the result to `ingest_clip_file` — so generated clips take the
exact same normalization path as uploads.

`generate_all_for_project` runs **sequentially in narrative order** (chaining is inherently serial;
see the "Regenerate All" entry in `Open_Issues.md` for the equivalent mistake made on the audio side
— do not repeat the parallel fan-out). After clip N is READY, extract its last frame via
`ffmpeg_utils.extract_last_frame` into clip N+1's `init_image_path`. Carry `style_prompt` and
`character_sheet` from `video_brief` into every request, plus `reference_image_paths` when the brief
has canonical subject images.

Runs as a FastAPI `BackgroundTask`, status polled — mirror `_generate_baseline_audio_for_project`
(projects.py:58). Endpoints: `POST .../video/clips/{clip_id}/generate`, `POST .../video/generate-all`.

- [ ] **Step 1:** Write the test with a **fake provider injected** — no API key, no network, no spend.
  Cover: status transitions PENDING → GENERATING → READY; a provider exception yields `FAILED` and
  does not abort the remaining clips; generate-all processes in `sequence_order`; clip N+1 receives
  clip N's tail as `init_image_path`; `style_prompt`/`character_sheet` reach every request.
- [ ] **Step 2:** Run; confirm FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run; confirm PASS.
- [ ] **Step 5:** Commit `feat: sequential provider-agnostic clip generation with tail chaining`.

---

## Task 6: Editor CRUD surface

**Files:** extend `app/api/routes/video.py`, test `backend/tests/test_video_routes_crud.py`

What Plan 5's UI will call. Nothing here knows about providers.

- `GET /api/v1/projects/{id}/video/clips` — ordered clips + `video_brief` + `subtitle_style`
- `PATCH .../video/clips/{clip_id}` — `VideoClipUpdate` (prompt, trim, sequence_order)
- `POST .../video/clips/reorder` — bulk reorder, mirroring `reorder_segments` (projects.py:389)
- `PATCH .../video/brief` — style/character sheet + subtitle style
- `DELETE .../video/clips/{clip_id}`

- [ ] **Step 1:** Write the test. Cover: list returns clips in `sequence_order` with the brief;
  trim values persist; reorder rewrites ordering contiguously; cross-user access 404s.
- [ ] **Step 2:** Run; confirm FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run; confirm PASS.
- [ ] **Step 5:** Commit `feat: video clip CRUD + brief endpoints for the studio editor`.

- [ ] **MANUAL CHECKPOINT B — API walkthrough.** Human drives the whole flow against a real campaign
  with the backend running (Swagger at `/docs` is fine): create campaign → clips provisioned with LLM
  shot prompts → upload 2-3 Flow clips → reorder → trim → list. Confirm the visual bible reads like
  usable art direction and the clip list is demo-shaped. GO/NO-GO into Plan 4.

---

## Done criteria for Plan 3

- Campaign creation yields a visual bible + one shot prompt per segment, with **no video API call**.
- A clip from any source (upload, asset, generated) reaches `READY` through one normalization path.
- Generate-all is sequential with tail-frame chaining and survives a per-clip failure.
- The full editor API surface exists and is provider-blind.
- **Every test passes with no Gemini key configured.**

**Next:** Plan 4 — ffmpeg assembly (fit clips to narration beats, concat, mux master narration, burn
ASS subtitles) producing the demo MP4. Plan 5 — the Audio|Video tabbed studio.
