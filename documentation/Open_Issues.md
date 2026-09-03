# Open Issues & Observations

**Last Updated**: 2026-09-02

## Critical / Blocking

- None currently. DB connection and migration are resolved.

## TTS — Audio Continuity (Partially resolved 2026-05-18)

- ~~**Option 2 (done, 2026-05-11)**~~: Reference audio chaining for clone-path segments. Reference tail bumped from 2s to 3s (2026-05-18).
- **Per-segment loudness normalization (done, 2026-05-18)**: `audio_normalize.py` implements silence trim → pad → LUFS normalize at –18 LUFS. Applied after pitch shift in `tts_engine.py`. Master export normalized to –16 LUFS with 25ms crossfade at segment boundaries.
- **Prosodic discontinuity (open)**: Pitch/rate still resets per segment for preset-speaker path. Full-script single-pass synthesis (Option 2) was deferred — re-editing complexity too high. Clone path benefits from 3s reference chaining. Accepted as architectural constraint of per-segment TTS.
- **Regenerate drops arc-continuity, incl. "Regenerate All" (open, noted 2026-06-17)**: BOTH single-segment "Regenerate Segment" AND "Regenerate All Segments" bypass the chained generator. `handleRegenerateAll` (InspectorPanel.tsx) is a parallel fan-out — `forEach(async …)` fires one isolated `/regenerate-segment` per segment concurrently. Each runs `audio.py::_run_regenerate_sync`, which synthesizes in isolation: NO `"continuing the emotional arc, {emotion}"` instruct prefix (presets) and NO prev-segment tail chaining (clones). The chaining logic exists ONLY in `_generate_baseline_audio_for_project` (projects.py:58), which is sequential, runs only on project creation (projects.py:220), and skips segments that already have audio (`if not segment.audio_url`, projects.py:73). So a global regenerate produces zero cohesion by construction — parallel execution also makes chaining impossible (it's inherently sequential: segment N's reference is N−1's fresh tail). **Fix direction**: add a `POST /projects/{id}/regenerate-all` that clears audio_url and re-runs `_generate_baseline_audio_for_project` sequentially; point the frontend button at it instead of the per-segment loop. NOTE: even fixed, presets only get the weak instruct prefix — true acoustic carryover (tail→reference) is clone-path only.
- **Preset speaker quality variance (observed 2026-06-17)**: Mixing preset speakers within one script reads as incoherent — there is no cross-speaker prosody anchoring, so e.g. a Vivian segment spliced among Aiden segments won't match in pitch/pace/energy. Practical guidance: pick ONE verified preset per campaign; if changing voice, regenerate ALL segments to it.
- **Preset native languages — only Aiden & Ryan are English (KEY, 2026-06-17)**: Per the Qwen3-TTS-12Hz-1.7B-CustomVoice HF model card, the 9 presets are: Vivian (F, Chinese), Serena (F, Chinese), Uncle_Fu (M, Chinese), Dylan (M, Chinese/Beijing), Eric (M, Chinese/Sichuan), **Ryan (M, English)**, **Aiden (M, English)**, Ono_Anna (F, Japanese), Sohee (F, Korean). Qwen's guidance: "use each speaker's native language for best quality." So for English fundraising scripts only **Aiden and Ryan** are appropriate — this is why Vivian (Chinese) sounded awful. **There is NO native-English female preset** → a female English narrator REQUIRES voice cloning. Our pickers (InspectorPanel.tsx:21, create-campaign-modal.tsx) currently expose Serena/Vivian/Dylan/Sohee with no language warning — a trap for an English-only tool. TODO: restrict or language-label the preset list (English-first; mark others as non-English/accented).

## TTS Engine — Planned Migration

- **Emotion + Cloning Limitation**: Qwen3-TTS Base model (used for zero-shot voice cloning) does NOT support `instruct`/emotion directives. Only the CustomVoice model (9 preset speakers) supports emotion control. This is an architectural limitation of the dual-model design.
- **Current workaround**: Emotion text is prepended to the synthesis text as `[emotion] text` for cloned voices. Effect is minimal.
- **CosyVoice 2/3 evaluated (2026-04-14)**: Has the right API (`inference_instruct2(text, instruct_text, prompt_speech)`) but blocked by: (1) Python 3.10 requirement (project uses 3.12), (2) no pip install — requires repo clone + submodules, (3) Windows+sox dependency issues, (4) GitHub issues #1314/#1400 report degraded voice similarity and garbled audio when combining instruct+clone.
- **Deferred until**: Qwen3-TTS 25Hz VoiceEditing model releases (no ETA) or CosyVoice gets a pip package + Python 3.12 support.
- **Migration scope**: Replace `TTSService` internals (`tts_engine.py`). The rest of the app is model-agnostic.
- **New candidates to evaluate (2026-06-17)**:
  - **IndexTTS-2** (arXiv 2506.21619, github.com/index-tts/index-tts) — strongest fit for our emotional-cohesion pain. Disentangles speaker identity from emotion (keep one timbre, control emotion independently), precise synthesis-duration control, English-centric zero-shot. Reportedly beats SOTA on WER, speaker similarity, AND emotional fidelity. This directly addresses "consistent voice + coherent, controllable emotion across segments." Need to check Python 3.12 + Windows + pip feasibility (the CosyVoice blockers).
  - **Chatterbox / Chatterbox-Turbo** — open-source, reportedly won a blind test 65.3% vs ElevenLabs 24.5%. Worth a quick listen test.
  - **ElevenLabs v3** (commercial, shipped Mar 2026) — most expressive studio-quality option, not real-time; viable as a paid fallback path given the app already supports a Claude-API-style provider toggle pattern.

## Frontend — Dashboard (Resolved 2026-03-24)

- ~~**Dashboard Visual Overhaul Needed**~~: RESOLVED — Full Moore brand applied (cream bg, white cards, red CTAs, Montserrat typography).
- ~~**Voice Profile Not Appearing**~~: RESOLVED — VoiceUpload now triggers VoiceList refresh via `onUploadSuccess` callback + `refreshKey` prop.
- ~~**No Loading/Progress Indicators**~~: RESOLVED — Added spinners to voice upload, validation, campaign creation, and studio loading.

## Frontend — Campaign Studio (Resolved 2026-03-24)

- ~~**Studio Visual Overhaul Needed**~~: RESOLVED — Moore brand applied to all studio components.
- ~~**Segment Timestamps Not Displayed**~~: RESOLVED — Start/end times shown in ScriptEditor and InspectorPanel.
- ~~**Segment Click Doesn't Navigate**~~: RESOLVED — Clicking a segment seeks the waveform to that segment's start time.
- ~~**Redundant Preview Section Button**~~: RESOLVED — Removed Preview Sequence button from header.

## Frontend — Remaining

- ~~**Cloned Voice Preview Beep**~~: RESOLVED (Session 3) — TTS models now load properly, generating real speech instead of sine waves.
- ~~**Cloned Voice Falls Back to Aiden**~~: RESOLVED (Session 3) — Voice profile UUID resolution and cloning pipeline working end-to-end.
- ~~**No Initial Audio on Load**~~: RESOLVED (Session 3) — Studio polls for audio and shows progress banner. Timestamps hidden until audio exists.
- ~~**No Voice Indicator in Studio**~~: RESOLVED (Session 4) — Voice name badges shown on ScriptEditor segment cards.
- **Campaign Creation No Progress**: After clicking "Generate", progress bar shown but could be more detailed.
- ~~**Type Safety**~~: RESOLVED (Session 8) — `frontend/types/next-auth.d.ts` added; all 6 `(session as any)` casts removed. Session timeout now shows re-login modal via `SessionExpiredModal.tsx`.

## Backend

- ~~**TTS Mock Mode**~~: RESOLVED (Session 3) — Both models load and generate real speech on CPU.
- **Tokenizer Warning**: `Qwen3TTSTokenizer` fails to load ("model type qwen3_tts not recognized by Transformers"). Embeddings use spectral fallback. May need `pip install --upgrade transformers` or install from source.
- **Audio Data**: Reference audio stored at absolute paths in `static/voice_uploads/`. Generated audio at `static/audio/`. Preview URLs served via static mount.
- ~~**FFmpeg Dependency**~~: RESOLVED (2026-06-27, video previs prereqs) — ffmpeg/ffprobe 8.1.2 installed via winget (`Gyan.FFmpeg`) and on PATH. Audio processing still WAV-only via `soundfile`; ffmpeg is used by the video pipeline (`app/services/video/ffmpeg_utils.py`), which also honours `FFMPEG_BINARY`/`FFPROBE_BINARY` overrides.
- **SoX Warning**: "SoX could not be found" at startup — cosmetic, doesn't affect functionality.
- **Setuptools Compatibility**: `pyloudnorm` requires `pkg_resources`. Fixed by pinning `setuptools<70.0.0`.

## Dashboard — Voice previews (open, noted 2026-09-02)

- **Every voice preview should say "Welcome to Aria Appeal"; none of them do.** Two distinct bugs
  behind one symptom:
  - **Cloned voices play the raw source clip.** `preview_url` is built in
    `app/schemas/voice_profile.py:34` as `/static/voice_uploads/{filename}` — it is literally the
    reference audio the user uploaded for cloning, so previewing plays back their whole original
    recording rather than a sample of the cloned voice.
  - **Preset ("emotional intelligence") voices have no preview at all.** Presets have no
    `reference_audio_path`, so `preview_url` resolves to `None`
    (`voice_profile.py:29`) and `VoiceList.tsx:195` hides the play button entirely.
  **Fix direction:** synthesize a fixed preview line through the normal TTS path for both voice
  types and cache it to `static/audio/preview_{profile_id}.wav` (clones) and
  `preview_preset_{speaker}.wav` (presets, shared across users). Generate lazily on first request,
  or at profile-creation time for clones. Point `preview_url` at the cached file rather than the
  upload.

- **Language-label the preset picker — reframe the trap as multi-language support (2026-09-02).**
  The preset list is majority non-English (see the native-languages entry above), which is currently
  an unlabelled trap. Decision: label rather than hide, and present it as a feature — the voice layer
  natively covers English, Chinese, Japanese and Korean, which is genuinely useful for a nonprofit
  serving diverse communities.
  - Group the picker by language with English first and Aiden/Ryan as the defaults.
  - **Preview each voice in its own native language**, or the label promises quality the audio
    contradicts — an English sample from Vivian is exactly the bad impression the labelling is meant
    to prevent. Suggested lines: English "Welcome to Aria Appeal"; Chinese "欢迎使用 Aria Appeal";
    Japanese "Aria Appeal へようこそ"; Korean "Aria Appeal에 오신 것을 환영합니다". Show the English
    gloss as caption text next to non-English voices so the greeting still reads as consistent.
  - **Scope honesty:** this makes the *voice* layer multi-language. Script generation, the studio UI,
    and subtitle rendering are still English-only. Say "multi-language narration" in the room, not
    "multi-language product" — the gap is easy to probe and cheap to be straight about.

## Testing (noted 2026-07-27)

- **5 stale backend tests fail, unrelated to current work (open)**: Verified pre-existing by
  running the suite at `5e03c28` (the commit before Plan 2 Task 3) — same 5 failures. They test
  architecture the project has since moved off:
  - `test_audio_generation.py::test_tts_service_qwen_local_fallback` and `::test_generate_audio_endpoint`
    — patch `generate_audio_task.delay`, i.e. Celery. The project uses FastAPI `BackgroundTasks`.
  - `test_manual_generation.py::test_llm_parsing` and `::test_llm_parsing_wrapper`
    — reference `app.services.llm.client`, removed in the Session 6 Claude-provider refactor.
  - `test_settings.py::test_settings_api` — POSTs `llm_provider: "openai"`, which the
    `Literal["claude","local"]` on `SystemSettings` rejects with 422.
  **Fix direction**: rewrite against the current architecture or delete. Until then they mask real
  regressions — the video work's 31 tests pass, but "5 failed" is the suite's normal state.
- **Anthropic API key printed to pytest stdout (open, minor)**: `test_settings_api` prints the full
  settings dict, including the live `anthropic_api_key` from `config.json`. `backend/config.json`
  is gitignored, but CI logs or a pasted test run would leak the key. Redact the print when fixing
  the test above.

## Infrastructure

- **Environment Variables**: `.env.local` for frontend, `.env` for backend.
- **DB Connection**: PgBouncer session mode pooler (port 5432). Connection string updated 2026-03-24.
- **Docker**: `docker-compose.yml` exists but Docker is not installed on the dev machine.

## Documentation

- **API Docs**: Swagger UI at `/docs`. OpenAPI spec not version-controlled.
- **CLAUDE.md**: At project root for persistent Claude session context.
