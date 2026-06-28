# Video Previsualization — Plan 2 Manual Test Plan

Companion to `2026-06-27-video-previs-02-engine.md`. **You (the human) run these.** Each
checkpoint maps to one task in Plan 2 and ends with a **GO / NO-GO** gate. The executing
agent must STOP at each 🔍 checkpoint and wait for your GO before the next task. Purpose:
catch ffmpeg/Veo reality problems early and avoid building orchestration on a broken engine.

## Before you start (one-time)

- **Use a FRESH terminal.** ffmpeg was installed in Plan 1 but only new shells see it on PATH.
  Confirm: `ffmpeg -version` and `ffprobe -version` both print a banner. If not, reopen your
  terminal (or set `FFMPEG_BINARY` / `FFPROBE_BINARY` to the full exe paths).
- Backend Python: from `backend/` use `./.venv/Scripts/python.exe`.
- A **Google Gemini API key with Veo access** is required for Checkpoint 4 only.

---

## Checkpoint 1 — Provider contracts (Task 1)

Run:
```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/test_video_provider_base.py -v
```
**PASS criteria:** 3 passed. No external deps involved.

**GO** if 3 passed. **NO-GO** otherwise → tell the agent what failed.

---

## Checkpoint 2 — ffmpeg utilities (Task 2)  ⚠ first real ffmpeg test

1. Run the automated tests **in a fresh shell where ffmpeg resolves** — the two
   `@requires_ffmpeg` tests must actually RUN (not skip):
```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/test_ffmpeg_utils.py -v
```
**PASS criteria:** `test_normalize_and_probe` and `test_extract_last_frame` show **PASSED**
(not SKIPPED). If they SKIP, ffmpeg isn't on PATH — fix the shell and rerun. A skip here
means you have NOT actually validated ffmpeg, so treat skip as NO-GO for this checkpoint.

2. Hands-on sanity check — normalize a real clip and inspect it:
```bash
cd "D:/Repo/Aria Appeal/backend"
# make a 3s test clip with audio at an odd size/fps:
ffmpeg -y -f lavfi -i "testsrc=size=640x360:rate=24:duration=3" -f lavfi -i "sine=frequency=440:duration=3" -shortest -pix_fmt yuv420p /tmp/cp2_src.mp4
./.venv/Scripts/python.exe -c "from app.services.video import ffmpeg_utils as u; print(u.normalize_clip('/tmp/cp2_src.mp4','/tmp/cp2_out.mp4')); print(u.probe_stream_info('/tmp/cp2_out.mp4')); print('duration_ms', u.probe_duration_ms('/tmp/cp2_out.mp4'))"
```
**Look for:** `{'width': 1920, 'height': 1080, 'fps': ~30.0, 'has_audio': False}` and a
duration around 3000ms.

3. Last-frame extraction — confirm a real PNG comes out:
```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -c "from app.services.video import ffmpeg_utils as u; print(u.extract_last_frame('/tmp/cp2_src.mp4','/tmp/cp2_last.png'))"
```
Open `/tmp/cp2_last.png` — it should be a single still frame from near the end.

**GO** if normalization yields 1920×1080 / 30fps / no audio AND the PNG opens.
**NO-GO** if dimensions/fps are wrong, audio survives, or the frame is blank.

---

## Checkpoint 3 — AssetVideoProvider (Task 3)

1. Drop a **real** mp4 into the assets dir (copy your CP2 output):
```bash
cd "D:/Repo/Aria Appeal/backend"
mkdir -p static/video/assets
cp /tmp/cp2_out.mp4 static/video/assets/demo_clip.mp4
```
2. Resolve it through the provider:
```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -c "
import asyncio
from app.services.video.asset_provider import AssetVideoProvider
from app.services.video.base import VideoGenRequest
p = AssetVideoProvider(assets_dir='static/video/assets')
res = asyncio.run(p.generate(VideoGenRequest(prompt='demo_clip.mp4')))
print('path:', res.video_path, '| duration_ms:', res.duration_ms)
"
```
**Look for:** the printed path points at `static/video/assets/demo_clip.mp4` and
`duration_ms` is a sensible number (~3000).

**GO** if it resolves the real file with a duration. **NO-GO** otherwise.

---

## Checkpoint 5 — Provider factory (Task 5)

(Do this before Checkpoint 4; the real-Veo test is last because it needs Task 6's key UI.)
```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -m pytest tests/test_video_factory.py -v
```
**PASS criteria:** 5 passed.

**GO** if 5 passed. **NO-GO** otherwise.

---

## Checkpoint 6 — Launcher Gemini key UI (Task 6)

1. Launch the GUI:
```bash
cd "D:/Repo/Aria Appeal"
python launcher.py
```
2. Open **⚙ Settings**. Confirm you see: a masked **Gemini API key** field, a **Veo model**
   field (default `veo-3.0-generate-001`), and a **video provider** toggle (gemini/local).
3. Paste your real Gemini API key, leave model as default, save/close the panel.
4. Confirm it persisted:
```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -c "import json; d=json.load(open('config.json', encoding='utf-8-sig')); print('has key:', bool(d.get('gemini_api_key'))); print('model:', d.get('veo_model'), '| provider:', d.get('video_provider'))"
```
**Look for:** `has key: True`, model `veo-3.0-generate-001`, provider `gemini`.

> Note: `config.json` is gitignored, so the real key is never committed.

**GO** if the key persists. **NO-GO** if the fields are missing or the key doesn't save.

---

## Checkpoint 4 — REAL Veo generation (Task 4)  💸 COSTS MONEY — run LAST, run ONCE

Only after Checkpoints 2 and 6 are GO. This makes **one** paid Veo API call. Do not loop.

```bash
cd "D:/Repo/Aria Appeal/backend"
./.venv/Scripts/python.exe -c "
import asyncio
from app.core.system_config import config_manager
from app.services.video.gemini_provider import GeminiVeoProvider
s = config_manager.get_settings()
assert s.gemini_api_key, 'No Gemini key in config — do Checkpoint 6 first'
p = GeminiVeoProvider(api_key=s.gemini_api_key, model=s.veo_model, out_dir='static/video/clips', poll_interval_s=10, timeout_s=300)
from app.services.video.base import VideoGenRequest
req = VideoGenRequest(prompt='A warm, slow push-in on a golden retriever puppy sitting in a sunny meadow', style_prompt='cinematic, soft natural light', duration_s=8)
print('Submitting to Veo — this takes ~30-90s...')
res = asyncio.run(p.generate(req))
print('DONE ->', res.video_path, '| duration_ms:', res.duration_ms)
"
```
**Then:** open the printed mp4 (under `backend/static/video/clips/veo_*.mp4`) and watch it.

**Look for:**
- The call completes within the timeout (no `TimeoutError`).
- An mp4 file exists and plays.
- The content roughly matches the prompt (a puppy in a meadow, ~8s, moving).
- (Optional) Run `ffprobe` on it to see native size/fps/codec — Veo output is the raw clip
  that normalization will later standardize.

**GO** if a real, playable, on-prompt clip is produced. **NO-GO** if the call errors, times
out, or returns nothing — capture the full error for the agent. If the API rejects the
`duration_seconds` or any config field, note the exact message: we may need to drop that
field for the installed Veo model version.

---

## After all checkpoints are GO

Plan 2 is validated end-to-end on real ffmpeg + real Veo. Tell the agent to proceed to
Plan 3 (generation + `video_service` orchestration), which wires these providers to the
`VideoClip` DB rows, background tasks, tail-frame chaining, and normalization-on-ingest.
