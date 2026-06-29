# Video Previsualization — Design Spec

**Date:** 2026-06-26
**Status:** Approved design — implementation not started
**Scope:** Phase 1 vertical demo slice ("Animatic assembler")

## Goal

Generate a moving **previsualization / animatic** of a fundraising appeal — better than
storyboards or stills for pitching clients on how the ad will look and feel. The output is a
**pitch artifact, not a finished ad**: if the client buys in, they shoot it for real. "Good,
not perfect" visual quality is acceptable and expected.

This came out of client-meeting feedback (2026-06-26): strong reception, with a "next phase"
ask for video + an in-studio editor to tweak it (drag clips, add subtitles).

## Scope

### In scope (Phase 1 vertical slice)

- Extend campaign generation to emit, alongside the spoken script: a per-segment video
  prompt + a campaign-level visual bible (style + character sheet).
- A `VideoProvider` abstraction with three implementations: pre-generated assets, live
  Google Veo (via Gemini API), and a future local provider (interface only).
- User upload of clips into a campaign, normalized through the same pipeline.
- Subject consistency via tail-frame chaining + character-sheet conditioning.
- An **Audio | Video** tabbed studio with a minimal "Animatic assembler" editor: reorder,
  replace, trim, subtitle toggle. Subtitles derive from existing segment text + timing.
- An ffmpeg assembly pipeline producing a final MP4 (video track + master narration +
  burned-in captions).

### Out of scope (deferred to Phase 2)

- Full independent-track NLE: free drag/place/trim of clips and audio on separate tracks,
  decoupled from segment boundaries. The Phase 1 data model is built forward-compatible so
  Phase 2 relaxes constraints rather than migrating data.
- Talking-head / lip-synced avatars.
- Music/SFX tracks.

### Non-goals

- Broadcast-grade output or perfect character consistency.
- Replacing the audio pipeline — video reuses the existing master narration.

## Prerequisites

- Install `ffmpeg` / `ffprobe` (currently missing; audio is WAV-only via `soundfile`). This
  becomes a hard requirement.
- A Google Gemini API key (Veo access), entered via the launcher Settings panel.
- New static dir `static/video/` (with `assets/` and `uploads/` subdirs), served like
  `static/audio/`.

## Architecture overview

Mirrors existing patterns: async SQLAlchemy throughout, long-running work via FastAPI
`BackgroundTasks` (no Celery/Redis), status polled by the studio exactly like audio
generation, provider abstraction modeled on the existing TTS/LLM provider-toggle pattern.

Key property: **the editor and assembly never touch a provider** — they read
`VideoClip.video_url`. Swapping Gemini for a local model later is one config switch plus one
new class.

## Data model

### New table: `videoclip`

(Table name is the lowercase class name, per existing convention — e.g. `voiceprofile`,
`scriptsegment`. FKs reference `project.id` and `scriptsegment.id`.)

| field | type | purpose |
|---|---|---|
| `id` | UUID PK | |
| `project_id` | FK → `project.id` | owner |
| `segment_id` | FK → `scriptsegment.id`, nullable | narration beat this clip illustrates (Phase 1 sets it; Phase 2 allows null = free clip) |
| `sequence_order` | int | order on the video track |
| `source_type` | enum: `generated` \| `asset` \| `uploaded` | where the video came from |
| `prompt` | str, nullable | per-clip Veo prompt (editable) |
| `video_url` | str, nullable | path under `/static/video/` once produced |
| `status` | enum: `pending` \| `generating` \| `ready` \| `failed` | drives polling |
| `duration_ms` | int, nullable | native clip length |
| `trim_start_ms` / `trim_end_ms` | int, nullable | in/out trim |
| `timeline_start_ms` / `timeline_end_ms` | int, nullable | position on the video track — derived from segment in Phase 1; storing now makes Phase 2 free placement trivial |
| `init_image_path` | str, nullable | seed frame for image-to-video / tail-chaining |
| `created_at` | datetime | |

### Project additions

- `video_brief` JSON column (mirrors existing `target_audience` JSON): campaign visual bible
  — style direction (palette, tone, setting, film look) + character sheet (named subjects
  with reusable physical descriptions). Also holds the assembled `video_master_url`.
- `subtitle_style` JSON column: enabled flag, font size, position, color.

### Subtitles

Derived from existing `scriptsegment.text` + `start_time_ms`/`end_time_ms`. No separate
subtitle table in Phase 1. Editing subtitle wording = editing segment text (already works).

### Migration

New table + new `Project` JSON columns via Alembic (`python -m alembic upgrade head`).

## VideoProvider contract

```python
@dataclass
class VideoGenRequest:
    prompt: str
    style_prompt: str | None        # campaign visual bible
    character_sheet: str | None     # reusable subject description
    init_image_path: str | None     # seed frame: tail-chaining or canonical ref
    duration_s: float = 8.0
    aspect_ratio: str = "16:9"

@dataclass
class VideoGenResult:
    video_path: str                 # downloaded/normalized mp4 under static/video/
    duration_ms: int

class VideoProvider(ABC):
    name: str
    @abstractmethod
    async def generate(self, req: VideoGenRequest) -> VideoGenResult: ...
```

### Implementations

- `GeminiVeoProvider` — calls Gemini `generate_videos` (Veo), polls the long-running
  operation to completion (with timeout), downloads the mp4. Honors `init_image_path` for
  image-to-video chaining. **Visuals only** — Veo's own audio track is discarded; the TTS
  narration is the soundtrack.
- `AssetVideoProvider` — resolves a pre-placed file from `static/video/assets/` and returns
  it. No API call. This is how pre-made clips attach without regeneration.
- `LocalVideoProvider` — stub / interface only; future company-hardware path.

### Resolution + config

- A `video_service` (parallel to `tts_service`) takes a `VideoClip`, picks the provider from
  `source_type` (`asset` → AssetProvider; `generated` → configured generated-backend, Gemini
  now / Local later), calls `generate`, writes the file, updates `status` / `video_url` /
  `duration_ms`. Runs in a `BackgroundTask`; the studio polls clip status.
- Config extends `config.json` + the launcher Settings panel: a video provider toggle +
  masked Gemini API key + Veo model picker — modeled on the existing Claude API key/model
  picker.

### Normalization on ingest

Every clip — Veo, asset, or upload — passes through one ffmpeg pass on ingest → uniform
format (H.264, 1920×1080, 30fps, audio stripped). Makes assembly trivial (clean concat) and
makes upload "just another source." This is load-bearing for assembly regardless of upload.

### Upload

`POST /projects/{id}/clips/upload` — accepts mp4/mov, stores under `static/video/uploads/`,
runs the shared normalization, sets `status=ready`, lands on the timeline like any other
clip. Genuinely useful (mix real client footage with AI previs) and a live-demo safety net.

## Generation flow

Extends existing campaign generation without disturbing how the spoken script is produced.

1. Script segments generate as today (text + per-segment emotion).
2. **New "art direction" LLM pass** (separate call, reuses `llm.py` `claude`/`local`
   toggle): takes the full script + campaign context, returns:
   - visual bible → `Project.video_brief` (style + character sheet)
   - one shot prompt per segment.
   Kept separate so script and visual direction can regenerate independently.
3. Create one `VideoClip` per segment (`source_type=generated`, `status=pending`,
   `prompt=shot prompt`, `segment_id` set, ordering/timeline mirrored from the segment).

**Generation is explicit, not automatic** — creating clips spends no Veo credits; clips sit
`pending` until the user hits "Generate" (per-clip or "Generate all video"), like audio.

### Chaining (generation-time only)

When `video_service` runs a sequential "generate all" in narrative order, after clip N
completes it extracts the last frame via ffmpeg → `init_image_path` for clip N+1. The
`style_prompt` + `character_sheet` go into every request so non-adjacent clips share
descriptors. Single-clip regenerate seeds from the canonical reference (or prior clip's tail
if present). **Reordering clips on the timeline does not re-trigger chaining.**

## ffmpeg assembly pipeline

New endpoint `POST /projects/{id}/video/export`, parallel to audio `/export`. Runs as a
`BackgroundTask`, status-polled, then preview/download.

Inputs: ordered normalized clips (with trims) + existing master narration WAV + subtitles
(segment text/timing) + `subtitle_style`.

Steps:
1. **Fit each clip to its narration beat.** Veo clips are ~8s fixed; segments vary. Clip
   longer than segment → trim to fit; clip shorter → **freeze last frame** to pad. Keeps
   audio/video locked. User's manual trim overrides the auto-fit.
2. **Concatenate** the fitted, uniform clips into one silent video track matching total
   narration length (fast concat, since normalization made them codec-compatible).
3. **Mux** the master narration onto the video track.
4. **Burn in subtitles** — emit an ASS file from segment text + timing (ASS so
   `subtitle_style` controls font size / position / color), burned via the `subtitles`
   filter.

Steps 3–4 fold into one final ffmpeg encode → MP4 under `static/video/`, served like audio.
Master URL stored on the project (`video_brief.video_master_url`) and returned by the
endpoint.

Fitting default is **freeze-last-frame padding** (animatic convention) over time-stretch
(slow-mo artifacts) or loop (reads as glitch).

## Tabbed studio editor

The studio header gains an **Audio | Video** toggle. The Audio tab is unchanged. The Video
tab reuses the shell:

- **Video preview** (16:9) with the assembled animatic + live subtitle overlay.
- **Clip inspector** (right): editable shot prompt, source badge, `Regenerate` / `Replace`
  (upload or pick asset), trim. Collapsible project-level controls: visual bible (style +
  character sheet), subtitle toggle/style.
- **Timeline strip** (bottom, full width): clips in order with thumbnails, per-clip status
  (`pending`/`generating`/`ready`/`failed`), durations, drag-to-reorder, trim handles, and a
  `Generate all video` action. Subtitle track beneath, derived from segments.

Transport/playback state is shared with the Audio tab (same Zustand store) — so the
playback-stop-on-unmount fix applies here too. Phase 1 stays an aligned single-video-track
strip; Phase 2 relaxes it into the free multi-track NLE.

## Risks & open questions

- **Veo latency on demo day.** Live generation is a ~30–60s wait (async operation), not
  instant. Set expectations; the uploaded-clip fallback de-risks a live flake.
- **Veo model/endpoint/pricing drift.** Confirm exact current model name, endpoint, and
  per-second cost at implementation time (provider versions change frequently).
- **Consistency is good, not perfect.** Faces may drift between non-adjacent clips; tail
  chaining handles adjacent continuity, character sheet handles the rest. Acceptable for
  previs.
- **Freeze-frame padding** accepted "for now"; revisit if it reads poorly.

## Success criteria

- Create a campaign → generated script + per-segment video prompts + visual bible.
- Attach pre-made clips as assets and upload a clip; generate one clip live via Veo.
- Assemble an end-to-end MP4: aligned clips + narration + burned-in subtitles.
- Do it all in the studio's Video tab with reorder / replace / trim / subtitle toggle.

## Phasing

- **Phase 1 (this spec):** the vertical slice above.
- **Phase 2 (future):** full independent-track NLE — free drag/place/trim of clips and audio
  on separate tracks, decoupled from segment boundaries.
