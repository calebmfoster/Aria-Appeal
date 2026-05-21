# Next Session Prompt: Phase X (Session 11) — Download, Per-Segment Waveforms & Segment Split

Read `CLAUDE.md`, `documentation/Project_Progress.md`, `documentation/Open_Issues.md` for full context.

---

## State After Session 10 (Complete)

Four features shipped:
- **Legal disclaimer gate** on voice cloning upload — checkbox-gated form in `VoiceUpload.tsx`
- **Voice profile usage indicator + inline rename** — `VoiceList.tsx` shows which campaigns use each profile; click name to rename; `PATCH /voice-profiles/{id}` backend endpoint
- **Campaign status polish** — progress bar (Tailwind, moore-red fill) + total duration on mastered campaigns in `CampaignList.tsx`
- **Segment drag-and-drop reorder** — `@dnd-kit` sortable in `ScriptEditor.tsx` with `GripVertical` handle; optimistic update + `PATCH /projects/{id}/segments/reorder` backend; `reorderSegments` store action

---

## SESSION 11 PRIORITIES

### Priority 1 — Download Mastered Audio

**Problem:** Users can master a campaign but cannot download the audio file.

**Implementation:**
- In the studio header (or wherever the Export/Master button lives), add a "Download" button that appears once `audioUrl` is set in the store
- Trigger a browser file download: create an `<a>` with `href=audioUrl` and `download="campaign-name.wav"` and click it programmatically
- The `audioUrl` is a path like `/static/audio/mastered_xxx.wav` served by FastAPI — prepend `NEXT_PUBLIC_API_URL` to make it absolute
- Button state: disabled until master audio exists; show spinner if export is in progress

**Key files:** Studio page/header component (find the Export/Master button), `frontend/store/studioStore.ts` (for `audioUrl`)

---

### Priority 2 — Per-Segment Mini Waveforms

**Problem:** Segment cards show timestamps but no visual shape of the audio — users can't see relative duration or audio content at a glance.

**Implementation:**
- Add a small waveform thumbnail to each `SortableSegmentItem` card in `ScriptEditor.tsx`
- Use wavesurfer.js `WaveSurfer.create({ container, waveColor, height: 32, interact: false })` — each segment renders its own mini waveform when `segment.audio_url` is set
- `interact: false` — no playback on these thumbnails; clicking the card still seeks the main waveform
- Only render if `segment.audio_url` exists; show nothing while awaiting audio
- Mount/destroy with `useEffect` on `audio_url` changes

**Key files:** `frontend/components/studio/ScriptEditor.tsx`

---

### Priority 3 — Segment Split

**Problem:** Users cannot split a long segment into two shorter ones, forcing awkward manual copy-paste + delete workflow.

**Implementation:**
- In the inline textarea (active segment), add a "Split here" button that appears in the toolbar when text is selected (or at cursor position)
- On click: take text before cursor as segment 1, text after cursor as segment 2
- Call `POST /projects/{id}/segments/split` with `{ segment_id, split_at_char }` (or just send both texts)
- Backend: delete the original segment + insert two new segments at `sequence_order` and `sequence_order + 1`, shifting later segments down
- Frontend: update store with two new segments replacing the original
- Clear master audio URL after split

**Key files:** `frontend/components/studio/ScriptEditor.tsx`, `backend/app/api/routes/projects.py`

---

### Priority 4 — Forgot Password Flow

**Problem:** No way to recover an account if a user forgets their password.

**Implementation:**
- Add "Forgot password?" link on the login page
- Two new backend endpoints:
  - `POST /auth/forgot-password` — accepts email, logs a reset token (store in DB or just log it since email sending isn't set up yet), returns 200 always (no enumeration)
  - `POST /auth/reset-password` — accepts `{ token, new_password }`, validates token, updates password
- Frontend: a `/reset-password?token=xxx` page with new password form
- For now, log the reset link to the backend console (no email service needed) — note clearly in UI that reset email "may take a few minutes"

**Key files:** `backend/app/api/routes/auth.py`, `frontend/app/` (new reset-password page), login page component

---

## Key Files Reference

| Feature | Key Files |
|---------|-----------|
| Download button | Studio page/header, `studioStore.ts` |
| Mini waveforms | `frontend/components/studio/ScriptEditor.tsx` |
| Segment split | `ScriptEditor.tsx`, `backend/app/api/routes/projects.py` |
| Forgot password | `backend/app/api/routes/auth.py`, `frontend/app/` |

## Session End Checklist

At end of session, update:
- `documentation/Project_Progress.md` — add Session 11 entry
- `documentation/Open_Issues.md` — close resolved items
- `documentation/Next_Session_Prompt.md` — set Session 12 priorities
- Commit + push to `https://github.com/calebmfoster/Aria-Appeal`
