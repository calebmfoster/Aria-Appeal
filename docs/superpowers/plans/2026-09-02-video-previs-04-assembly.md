# Video Previsualization — Plan 4: ffmpeg Assembly

**Goal:** Turn ready clips + segment narration + subtitle style into one playable MP4. This is the
demo artifact — the thing you put on screen for the CTO/CAO/CIO the week of 2026-09-14.

**Source spec:** `docs/superpowers/specs/2026-06-26-video-previsualization-design.md`
**Builds on:** Plan 1 (model), Plan 2 (ffmpeg_utils). Deliberately does **not** depend on Plan 3 —
the Make-A-Wish fixture already provides ready clips, so assembly can be built and demoed first.

---

## Two deviations from the spec, and why

**1. Window = `max(clip duration, narration duration)`, not "fit clip to narration beat."**

The spec assumed every clip is a fixed ~8s Veo blob that must be cut down to its narration. The real
footage inverted that: the Flow film is a finished 23.85s piece whose shot pacing is intentional, and
the narration was deliberately written *under* each scene window. Trimming clips to narration length
would chop the film — scene 3 would lose 1.17s of a 4.0s shot.

So the rule is one line: each beat's window is the longer of its clip and its narration.
- Clip longer than narration (our fixture, every scene) → keep the clip, pad the audio with silence.
- Narration longer than clip (the Veo case) → freeze the clip's last frame to cover the overrun.
- Explicit `trim_start_ms` / `trim_end_ms` always win — that is the editor's override, per spec.

The cost is that a clip much longer than its narration plays with trailing silence. That is an
editorial problem with an editorial fix (trim it), not an assembly problem.

**2. Assembly builds its own audio track from segments; it does not reuse the mastered WAV.**

`mastering_service.master_project` concatenates segments with 25ms crossfades into a gapless master.
That is correct for the audio product — a radio spot — but it is 20.9s against 23.85s of picture, and
gapless means every scene after the first drifts out of sync. Video assembly instead places each
segment's WAV at its own window start and pads to length, which guarantees per-scene lock.

The mastered WAV remains the audio deliverable. These are different artifacts with different
requirements, and conflating them would desync the film.

---

## Task 1: Timeline computation (pure)

**Files:** create `backend/app/services/video/assembly.py`, test `backend/tests/test_assembly_timeline.py`

```python
@dataclass
class Beat:
    clip_path: str          # absolute path to the source clip
    audio_path: str | None  # absolute path to the segment WAV, None if unvoiced
    text: str               # subtitle text
    start_ms: int           # position on the assembled timeline
    window_ms: int          # total duration of this beat
    audio_ms: int           # narration length (<= window_ms)
    pad_ms: int             # freeze-frame padding needed (0 when clip >= narration)
    trim_start_ms: int
    trim_end_ms: int | None

def compute_timeline(clips, segments, clip_dir, audio_dir) -> list[Beat]: ...
```

No ffmpeg, no DB, no I/O beyond path joining — a pure function over ORM rows so the fitting maths is
testable in isolation.

- [ ] **Step 1:** Write the test. Cover: clip longer than narration yields `pad_ms == 0` and
  `window_ms == clip duration`; narration longer yields `pad_ms > 0` and `window_ms == audio_ms`;
  explicit trims shorten the window; `start_ms` values are contiguous and cumulative; a clip with no
  segment audio still produces a beat with `audio_ms == 0`; clips are ordered by `sequence_order`
  regardless of input order.
- [ ] **Step 2:** Run; confirm FAIL. **Step 3:** Implement. **Step 4:** Run; confirm PASS.
- [ ] **Step 5:** Commit.

## Task 2: ASS subtitle generation (pure)

**Files:** extend `assembly.py`, test `backend/tests/test_assembly_subtitles.py`

```python
def build_ass(beats, style: dict) -> str: ...
```

ASS rather than SRT so `subtitle_style` can drive font size, position and colour. Each cue runs from
`beat.start_ms` to `beat.start_ms + beat.audio_ms` — captions must disappear during the trailing
silence of a long clip, not hang on screen.

- [ ] **Step 1:** Write the test. Cover: one Dialogue line per voiced beat; cue timings match
  narration not window; `enabled: False` yields no dialogue lines; colour converts to ASS `&HBBGGRR`
  (reversed byte order — the classic mistake); position maps to an alignment value; text containing
  a comma or newline does not corrupt the comma-delimited Dialogue line.
- [ ] **Step 2-4:** FAIL, implement, PASS. **Step 5:** Commit.

## Task 3: ffmpeg fitting primitives

**Files:** extend `ffmpeg_utils.py`, test `backend/tests/test_ffmpeg_fitting.py`

```python
def trim_clip(src, dst, start_ms, end_ms) -> str: ...
def freeze_pad_clip(src, dst, pad_ms) -> str: ...   # hold the last frame
def pad_audio(src, dst, total_ms) -> str: ...       # trailing silence to length
def silent_audio(dst, duration_ms) -> str: ...      # for unvoiced beats
```

- [ ] **Step 1:** Write the test, `@requires_ffmpeg`, synthesizing inputs with lavfi as
  `test_ffmpeg_utils.py` does. Assert output durations within tolerance and that freeze-padding
  actually extends rather than truncating.
- [ ] **Step 2-4:** FAIL, implement, PASS. **Step 5:** Commit.

## Task 4: Assemble

**Files:** extend `assembly.py`, test `backend/tests/test_assembly_integration.py`

```python
def assemble(beats, out_path, style, work_dir=None) -> str: ...
```

Per beat: normalize → trim → freeze-pad if needed → per-beat audio padded to window. Then concat the
video parts, concat the audio parts, and mux + burn subtitles in a single final encode.

- [ ] **Step 1:** Write the test, `@requires_ffmpeg`, with two synthesized clips and two short WAVs.
  Assert the output exists, its duration equals the sum of windows within tolerance, it has both a
  video and an audio stream, and it is 30fps at the normalization target.
- [ ] **Step 2-4:** FAIL, implement, PASS. **Step 5:** Commit.

## Task 5: Export endpoint

**Files:** `app/api/routes/video.py` (create if Plan 3 hasn't), test `backend/tests/test_video_export_route.py`

- `POST /api/v1/projects/{id}/video/export` — runs as a `BackgroundTask`, mirroring the audio export
- `GET /api/v1/projects/{id}/video/export` — status + `video_master_url`

Result URL is stored on `Project.video_brief.video_master_url` per spec.

- [ ] **Step 1:** Write the test with assembly mocked — route behaviour only, no ffmpeg. Cover: 400
  when clips aren't all ready; cross-user 404; status transitions.
- [ ] **Step 2-4:** FAIL, implement, PASS. **Step 5:** Commit.

## Task 6: Assemble the real demo

- [ ] Run assembly over the seeded Make-A-Wish fixture and produce the MP4.
- [ ] **MANUAL CHECKPOINT — watch it.** Narration locked to picture per scene, captions readable and
  timed to speech, no black frames at cuts, audio not clipping. This is the demo artifact.

---

## Done criteria

- One MP4: clips in order, narration locked per scene, burned-in captions, 30fps, correct duration.
- Timeline and subtitle logic unit-tested without ffmpeg; fitting and assembly tested with it.
- Export endpoint exists and is provider-blind.
- **The Make-A-Wish demo film plays end to end.**
