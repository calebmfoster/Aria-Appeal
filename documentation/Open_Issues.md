# Open Issues & Observations

**Last Updated**: 2026-06-17

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
- **FFmpeg Dependency**: `ffmpeg`/`ffprobe` missing. Audio processing limited to WAV-only via `soundfile`.
- **SoX Warning**: "SoX could not be found" at startup — cosmetic, doesn't affect functionality.
- **Setuptools Compatibility**: `pyloudnorm` requires `pkg_resources`. Fixed by pinning `setuptools<70.0.0`.

## Infrastructure

- **Environment Variables**: `.env.local` for frontend, `.env` for backend.
- **DB Connection**: PgBouncer session mode pooler (port 5432). Connection string updated 2026-03-24.
- **Docker**: `docker-compose.yml` exists but Docker is not installed on the dev machine.

## Documentation

- **API Docs**: Swagger UI at `/docs`. OpenAPI spec not version-controlled.
- **CLAUDE.md**: At project root for persistent Claude session context.
