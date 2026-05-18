# Next Session Prompt: Phase X (Session 9) — Tier 3 Segment & Waveform Features

Read `CLAUDE.md`, `documentation/Project_Progress.md`, `documentation/Open_Issues.md` for full context.

---

## State After Session 8 (Complete)

App is published to private GitHub at `https://github.com/calebmfoster/Aria-Appeal`.

Audio cohesion is fully implemented:
- Per-segment normalization: –45 dBFS silence trim → 30ms/120ms padding → –18 LUFS in `backend/app/services/audio_normalize.py` + wired into `tts_engine.py` after pitch shift
- Master export: 25ms logarithmic crossfade stitching + –16 LUFS final pass in `mastering_service.py`
- Clone-path reference tail: 3.0 s (was 2.0 s) in `projects.py`

NextAuth type safety resolved — `frontend/types/next-auth.d.ts` added, 6 casts removed.
Session timeout handled — `SessionExpiredModal.tsx` + `lib/api.ts` `apiFetch` wrapper added.

---

## SESSION 9 PRIORITIES

### Priority 1 — Inline Text Editing in ScriptEditor

**Problem:** Users must click a segment in ScriptEditor, then scroll to InspectorPanel to edit text. This two-pane friction adds steps to the most common workflow.

**Implementation:**
- `frontend/components/studio/ScriptEditor.tsx` — add inline `<textarea>` that appears on double-click of a segment's text `<p>`. On blur, call `scheduleSave` from the store (or pass it down as a prop from the store actions).
- Wire to existing `updateSegment(id, { text })` + `dirtySegments` tracking (already works via InspectorPanel — ScriptEditor just needs to call the same actions).
- Inspector should stay in sync automatically since both read from Zustand `script`.
- Keep `scheduleSave` in InspectorPanel for now; extract to a shared hook later if needed.

**Key files:** `frontend/components/studio/ScriptEditor.tsx`, `frontend/store/studioStore.ts`

---

### Priority 2 — Segment Management (Add / Delete)

Start with add and delete only. Split/merge/reorder are lower priority.

**Backend endpoints needed:**

```python
# POST /api/v1/projects/{project_id}/segments
# Creates a new empty segment at given sequence_order, shifts others down
body: { text: str, sequence_order: int, emotion?: str }
response: ScriptSegmentRead

# DELETE /api/v1/projects/{project_id}/segments/{segment_id}
# Deletes segment + its audio file; recalculates timestamps
response: { message: str }
```

**Frontend:**
- "Add segment" button below each ScriptEditor card (+ at bottom of list)
- Confirmation dialog on segment delete (reuse existing confirm pattern from VoiceList/CampaignList)
- Store actions: `addSegment(segment)`, `removeSegment(id)` — update `script` array, reset `activeSegmentId` if deleted
- After delete, call `handleGenerateFullAudio` to re-export master

**Key files:** `backend/app/api/routes/projects.py`, `frontend/components/studio/ScriptEditor.tsx`, `frontend/store/studioStore.ts`

---

### Priority 3 — Waveform Controls

Three additions to `WaveformVisualizer.tsx`:

1. **Volume slider** — `ws.setVolume(value)` (0–1 float). Add a small `<input type="range">` in the waveform toolbar.
2. **Skip ±5s buttons** — `ws.skip(5)` / `ws.skip(-5)`. Two icon buttons (SkipForward5 / SkipBack5 from lucide).
3. **Zoom slider** — `ws.zoom(pxPerSec)`. WaveSurfer v7 supports `zoom()` directly. Add `+/-` buttons or a range slider. Start at default (around 50 px/s), max ~300.

**Key file:** `frontend/components/studio/WaveformVisualizer.tsx` (WaveSurfer instance is at `wsRef.current`)

---

### Priority 4 — Migrate Call Sites to `apiFetch`

`frontend/lib/api.ts` exists with the `apiFetch` wrapper (fires `aria:unauthorized` on 401) but call sites still use raw `fetch`. Migrate the highest-traffic ones:

- `InspectorPanel.tsx` — save segment (PATCH), regenerate-segment (POST), poll task (GET)
- `CampaignList.tsx` — list (GET), delete (DELETE)
- `VoiceList.tsx` — list (GET), delete (DELETE)
- `create-campaign-modal.tsx` — create (POST)
- `studio/[id]/page.tsx` — export (POST), fetch voice profiles (GET)

Skip `VoiceUpload.tsx` for now — FormData upload needs special handling (no Content-Type header override).

---

## Key Files Reference

| Feature | Key Files |
|---------|-----------|
| Inline text editing | `frontend/components/studio/ScriptEditor.tsx`, `studioStore.ts` |
| Segment add/delete | `backend/app/api/routes/projects.py`, `ScriptEditor.tsx`, `studioStore.ts` |
| Waveform controls | `frontend/components/studio/WaveformVisualizer.tsx` |
| apiFetch migration | `frontend/lib/api.ts`, all component files listed above |

## Session End Checklist

At end of session, update:
- `documentation/Project_Progress.md` — add Session 9 entry
- `documentation/Open_Issues.md` — close resolved items
- `documentation/Next_Session_Prompt.md` — set Session 10 priorities
- Commit + push to `https://github.com/calebmfoster/Aria-Appeal`
