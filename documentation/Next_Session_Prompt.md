# Next Session Prompt: Phase X (Session 8) — Audio Cohesion Planning + Tier 3

Read `CLAUDE.md`, `documentation/Project_Progress.md`, `documentation/Open_Issues.md` for full context.

---

## State After Session 7 (Complete)

All Session 6 breakage is repaired AND additional bugs caught in testing are fixed. The app is fully functional:

- `backend/config.json` — UTF-8, `llm_provider: "claude"`, API key populated. `ANTHROPIC_API_KEY` also stored in `backend/.env` as durable fallback (survives config resets). `system_config.py` reads env var when config value is empty.
- `frontend/.env.local` — back on localhost.
- `default_speaker` / `default_pitch_shift` — removed from launcher, `SystemSettings`, `projects.py`, `tts_engine.py`. "Aiden" is hardcoded fallback in `tts_engine.py`.
- `dist/AriaAppealLauncher.exe` — rebuilt 2026-05-18. Settings panel no longer shows Default Voice or Default Pitch rows.
- **Voice-switching bug fixed** — `fetchProjectData` now resets `audioUrl`, `activeSegmentId`, `isPlaying`, `generatingSegments`, `saveStatus` on every campaign load. Previously Campaign A's stale `audioUrl` persisted into Campaign B, blocking the export trigger and playing the wrong audio.
- **`speaker_preset` in store** — segment mapping, dirty tracking, `markSegmentClean` all include `speaker_preset`.
- **WaveformVisualizer AbortError** — suppressed via `ws.on('error')` handler.

---

## SESSION 8 FIRST TASK: Opus Planning Session — Audio Cohesion

**Do this before any Tier 3 feature work.** This needs a design decision, not just implementation.

### The Problem

Generated campaigns sound like a collection of independently-recorded clips rather than a single cohesive recording. Two distinct issues compound each other:

**Issue A — Loudness variation:**
Each segment is synthesized in a separate TTS call. The model's output amplitude varies between calls — one segment may be notably louder or quieter than the next. There is currently zero loudness normalization between segments.

**Issue B — Prosodic discontinuity:**
- Pitch, speaking rate, and energy reset at the start of each segment. A segment can end with rising intonation and the next starts with falling intonation.
- The silence at segment boundaries is uncontrolled: some segments have long trailing silence, some cut abruptly. The 25ms crossfade at stitch points in `mastering_service.py` softens the seam but cannot fix a prosodic mismatch.
- Each TTS call has no acoustic "memory" of the previous segment.

**What's already in place (partial mitigations):**
- **Clone-path segments**: Reference audio chaining — the last 2 seconds of segment N's audio is fed as reference audio into segment N+1's TTS call. This gives the model some prosodic context. Works for cloned voices only.
- **Preset-path segments**: The emotion instruct string is prefixed with `"continuing the emotional arc, {emotion}"` for segments after the first. This is a soft hint with limited effect — the model still resets each call.

### Architecture Context

The codebase has a **dual TTS path** that must be respected in any solution:

| Path | Model | Trigger | Emotion support |
|------|-------|---------|-----------------|
| Preset speakers | `Qwen3-TTS-12Hz-1.7B-CustomVoice` | `segment.speaker_preset` is set | Full instruct support |
| Cloned voice | `Qwen3-TTS-12Hz-1.7B-Base` | `segment.voice_profile_id` → `VoiceProfile.reference_audio_path` | None (Base model is instruct-blind) |

Key constraint: the Base model does NOT support emotion/instruct text. Any solution that routes through it cannot control prosody via text prompting.

**Key files:**
- `backend/app/services/tts_engine.py` — `TTSService.generate_audio()`, `_generate_preset_voice()`, `_generate_cloned_voice()`, `_apply_pitch_shift()`
- `backend/app/api/routes/projects.py` — `_generate_baseline_audio_for_project()` — the loop that generates all segments; handles reference audio chaining; calls `generate_audio_task()`
- `backend/app/worker.py` — `generate_audio_task()` — sync wrapper called by both baseline generation and per-segment regeneration
- `backend/app/services/mastering_service.py` — `stitch_segments()` — applies 25ms crossfades when exporting
- `backend/alembic/versions/` — migration history if DB schema changes are needed

**Audio processing libraries available:**
- `soundfile` — WAV read/write (ffmpeg NOT available)
- `scipy` — resampling, signal processing (used for pitch shift)
- `pyloudnorm` — LUFS measurement and normalization (installed, requires `setuptools<70.0.0`)
- `pydub` — AudioSegment manipulation (used for stitching/crossfades)
- `numpy` — array ops

**ffmpeg/ffprobe are NOT installed** — no MP3, no ffmpeg-based processing.

### Options to Evaluate

**Option 1 — Post-processing normalization chain (per-segment, after generation)**
After each segment WAV is written, apply a normalization pipeline in `tts_engine.py`:
1. Strip leading/trailing silence below a threshold (e.g., –50 dBFS) — makes boundaries consistent
2. Add fixed silence padding (e.g., 50ms head, 100ms tail) — controls pacing
3. LUFS normalization to a target (e.g., –18 LUFS for speech)
4. Optional: light spectral matching against a reference segment (first segment or a target EQ curve)

Pros: Works for both TTS paths. Non-destructive (original segment audio replaced). Simple to implement incrementally. Does not require any architectural changes.
Cons: Does not fix prosodic discontinuity (pitch/rate resets). Addresses loudness and silence only.

**Option 2 — Full-script single-pass synthesis (preset voice path)**
For preset-speaker campaigns: concatenate all segment texts with punctuation into a single TTS call. Get back one continuous WAV. Split it back into per-segment files using forced alignment or silence detection at expected sentence boundaries.

Pros: Best possible prosodic continuity for preset voices — the model reads the whole script in context.
Cons: Significantly complicates re-editing (changing one segment requires re-synthesizing the whole script or managing seam splicing). Splitting on silence is fragile if the model doesn't pause at sentence boundaries. Does not apply to clone path. Would require a new "rebuild all audio" flow vs. per-segment generation.

**Option 3 — Enhanced reference audio chaining (clone path)**
Already implemented for clone path. Potential improvements:
- Increase tail length from 2s to 3-4s to give more prosodic context
- Also capture the HEAD of the next segment's expected text and pass as reference_text to help the model anticipate the transition
- Evaluate whether chaining quality degrades over many segments (accumulated drift)

**Option 4 — Mastering-layer normalization (at stitch time, not generation time)**
Instead of normalizing each segment individually, normalize the full stitched master in `mastering_service.py`:
- Apply a LUFS normalization pass across the whole master WAV after stitching
- Apply a gentle compressor/limiter to even out dynamics
- This is downstream-only; it doesn't fix prosodic discontinuity but ensures the exported campaign has consistent loudness

Pros: Single pass, no per-segment processing. Doesn't touch individual segment files (which may be re-used for segment-level playback).
Cons: Individual segment playback in the studio still sounds inconsistent. Doesn't help during generation preview.

**Option 5 — Hybrid**
Option 1 (per-segment post-processing: silence strip, pad, LUFS normalize) + Option 4 (master-level normalization at export) + Option 3 improvements for clone path. No full-script synthesis — accept prosodic discontinuity as an inherent constraint of per-segment TTS, mitigate everything else.

### Questions for the Planning Session

1. Is full-script synthesis (Option 2) worth the re-editing complexity tradeoff? Or do we accept that preset-voice prosody will have some discontinuity and focus on loudness/silence?
2. Should per-segment normalization target –18 LUFS or another level? (–23 LUFS is broadcast standard but may sound quiet for fundraising audio)
3. Silence stripping threshold and padding values — what sounds natural for a donor-facing campaign?
4. Does the spectral matching (EQ matching across segments) provide enough value to justify the complexity?
5. Should silence/padding/LUFS normalization be applied during generation (in `tts_engine.py`) or deferred to stitch time (in `mastering_service.py`)? Per-segment is better for studio preview; stitch-time is simpler.
6. Should loudness normalization be a global on/off setting in `SystemSettings`, or always-on?

### Deliverable Expected from Planning Session

A concrete implementation plan with:
- Which options to implement (and in what order)
- Exact functions to add/modify with signatures
- Target values (LUFS level, silence threshold, padding ms)
- How per-segment regeneration (single segment re-gen from InspectorPanel) interacts with the new pipeline
- Whether any DB schema or API changes are needed
- Test criteria: what does "good enough" sound like?

---

## Tier 3 Features (After Audio Cohesion is Resolved)

1. **Inline Text Editing** — click segment text in ScriptEditor to edit directly
2. **Segment Management** — add/delete/split/merge/reorder segments
3. **Waveform Controls** — zoom, volume slider, skip forward/back 5s
4. **Session Timeout Handling** — detect 401s globally, show re-login modal
5. **Security Hardening** — extend NextAuth session type, eliminate `(session as any)` casts
6. **Mobile Responsive** — dashboard stacking, "use desktop" for studio

## Key Files for Tier 3

| Feature | Key Files |
|---------|-----------|
| Inline text editing | `frontend/components/studio/ScriptEditor.tsx`, `studioStore.ts` |
| Segment management | `backend/app/api/routes/projects.py`, `ScriptEditor.tsx`, `studioStore.ts` |
| Waveform controls | `frontend/components/studio/WaveformVisualizer.tsx` |
| Session timeout | `frontend/lib/api.ts` or global fetch wrapper |
| Type safety | `frontend/types/next-auth.d.ts` |
