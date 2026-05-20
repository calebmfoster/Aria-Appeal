# Next Session Prompt: Phase X (Session 10) — Voice Cloning Legal Disclaimer & Dashboard Polish

Read `CLAUDE.md`, `documentation/Project_Progress.md`, `documentation/Open_Issues.md` for full context.

---

## State After Session 9 (Complete)

Studio is significantly more polished:
- **Inline text editing**: single-click to edit, click-off to deselect back to Global Settings
- **Segment CRUD**: add/delete with waveform auto-update
- **Waveform controls**: volume, skip ±5s, zoom
- **Voice picker**: Emotional Intelligence / Cloned tab toggle on both global and per-segment selects; auto-syncs to segment's voice type
- **apiFetch migration**: all fetch calls covered; 401s surface SessionExpiredModal
- All session 9 changes committed and pushed to `https://github.com/calebmfoster/Aria-Appeal`

---

## SESSION 10 PRIORITIES

### Priority 1 — Legal Disclaimer for Voice Cloning

**Problem:** Users can upload any audio and generate a cloned voice with no acknowledgment of rights/permissions. This is a legal and trust risk.

**Flow:**
- In `frontend/components/dashboard/VoiceUpload.tsx`, gate the upload form behind a consent step
- Before the form fields are shown (or as a blocking modal/step), display a clear disclaimer:
  > "By uploading this audio, you confirm that you have the explicit rights and consent of the voice owner to use this recording for AI voice synthesis. Uploading audio without authorization may violate applicable laws."
- User must check a checkbox to proceed — the form fields and submit button are disabled/hidden until accepted
- Checkbox state is local (no backend storage needed for now)
- Keep the flow clean: one step, no multi-page wizard

**Outcome paths:**
- **Accepted** → form unlocks, user proceeds normally
- **Not accepted** → form remains locked, no upload possible

**Key file:** `frontend/components/dashboard/VoiceUpload.tsx`

---

### Priority 2 — Segment Reorder (Drag-and-Drop)

**Problem:** Users cannot reorder segments without deleting and re-adding them.

**Implementation:**
- Add drag-and-drop to `ScriptEditor.tsx` using `@dnd-kit/core` + `@dnd-kit/sortable` (already a good fit for the card list)
- On drop, call a new backend endpoint `PATCH /projects/{id}/segments/reorder` with the new ordered array of segment IDs
- Backend updates `sequence_order` for all affected segments in one transaction
- Store: update `script` array order after confirmed reorder
- After reorder, clear master audio URL (stale) — user re-exports manually

**Key files:** `frontend/components/studio/ScriptEditor.tsx`, `backend/app/api/routes/projects.py`

---

### Priority 3 — Voice Profile Improvements

Two small additions to the voice profile dashboard:

1. **Usage indicator** — show which campaigns use each voice profile (query `/projects` and cross-reference `voice_profile_id` / `speaker_preset` in segments)
2. **Rename voice profile** — inline edit for profile name in VoiceList (PATCH to `/voice-profiles/{id}`)

**Key files:** `frontend/components/dashboard/VoiceList.tsx`, `backend/app/api/routes/voice_profiles.py`

---

### Priority 4 — Campaign Status Polish

- Campaign cards in `CampaignList.tsx` currently show Draft / Generated / Mastered status
- Add audio progress bar: `{audioReady}/{segmentCount} segments` is already shown — convert to a small visual progress bar
- Show total duration on mastered campaigns (derive from segment timestamps)

**Key file:** `frontend/components/dashboard/CampaignList.tsx`

---

## Key Files Reference

| Feature | Key Files |
|---------|-----------|
| Legal disclaimer | `frontend/components/dashboard/VoiceUpload.tsx` |
| Segment reorder | `frontend/components/studio/ScriptEditor.tsx`, `backend/app/api/routes/projects.py` |
| Voice profile improvements | `frontend/components/dashboard/VoiceList.tsx` |
| Campaign status polish | `frontend/components/dashboard/CampaignList.tsx` |

## Session End Checklist

At end of session, update:
- `documentation/Project_Progress.md` — add Session 10 entry
- `documentation/Open_Issues.md` — close resolved items
- `documentation/Next_Session_Prompt.md` — set Session 11 priorities
- Commit + push to `https://github.com/calebmfoster/Aria-Appeal`
