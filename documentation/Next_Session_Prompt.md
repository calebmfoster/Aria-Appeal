# Next Session Prompt: Video Previsualization — Vertical Slice (Phase 1)

Read `CLAUDE.md`, `documentation/Project_Progress.md`, `documentation/Open_Issues.md`, and
`documentation/Product_Roadmap.md` (Tier V) for full context.

---

## State After Session 12 (2026-06-26)

- **Client meeting:** strong reception. Main ask: add video to the appeal + a studio editor
  to tweak it. Reframed as a **previsualization / animatic** tool for pitching clients.
- **Bug fixed:** studio audio no longer keeps playing after navigating away
  (`WaveformVisualizer.tsx` teardown now stops playback + resets `isPlaying`).
- **Design in progress:** the video previsualization spec is being authored under
  `docs/superpowers/specs/`. Implementation has **not** started — do not build until the
  spec is approved and an implementation plan exists.

---

## NEXT PRIORITIES

### Priority 1 — Video Previsualization, Phase 1 (Vertical Demo Slice)

Build per the approved spec. Phasing within the slice (see spec for detail):

1. **Prerequisites:** install `ffmpeg`/`ffprobe`; obtain a Gemini API key; add `static/video/`.
2. **Data model:** `videoclip` table + `Project.video_brief` / `Project.subtitle_style` JSON
   columns + Alembic migration.
3. **`VideoProvider` abstraction:** `asset` + live Gemini (Veo) providers behind one
   interface; wired through the existing settings/provider-toggle pattern.
4. **Generation:** extend campaign generation to emit per-segment video prompts + a
   campaign visual bible (style + character sheet); tail-frame chaining for consistency.
5. **ffmpeg assembly:** video track + master narration + burned-in captions → MP4.
6. **Studio Audio|Video tabs:** minimal editor (reorder / replace / trim / subtitle toggle).

### Priority 2 — Outstanding Tier 3 Gaps (as capacity allows)

- Forgot-password / reset flow (`auth.py`, new `/reset-password` page)
- Per-segment mini waveforms in `ScriptEditor.tsx`
- Segment split
- "Regenerate All" arc-continuity fix (see `Open_Issues.md` — currently bypasses chaining)

---

## Session End Checklist

At end of session, update:
- `documentation/Project_Progress.md` — add the session entry
- `documentation/Open_Issues.md` — close resolved items, log new discoveries
- `documentation/Next_Session_Prompt.md` — set the next priorities
- Commit + push to `https://github.com/calebmfoster/Aria-Appeal`
