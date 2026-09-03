# Next Session Prompt: Video Previsualization — Plan 5 (Audio | Video Studio)

Read `CLAUDE.md`, `documentation/Project_Progress.md`, `documentation/Open_Issues.md`, and
`documentation/Product_Roadmap.md` (Tier V) for full context.

---

## HARD DEADLINE

**Client demo to the CTO, CAO and CIO — week of 2026-09-14.** Roughly ten working days from
2026-09-02.

The audience is a technical/administrative buying committee, not a creative one. They will probe
architecture, vendor lock-in and cost model more than aesthetics, and have signalled they may want a
different video provider. Two rules follow:

1. **Build the demo on Flow-sourced / uploaded clips, never on live Veo.** No paid API dependency, no
   live generation call in the room. The `VideoProvider` abstraction means this costs us nothing
   architecturally — and provider-swappability is a selling point to say out loud.
2. **Pre-generate everything before the meeting.** Nothing generated live on stage.

---

## State after Session 13 (2026-09-02)

**Plans 2 and 4 are fully coded and executed** on `feat/video-previs` — 81 backend tests pass
(5 pre-existing failures unrelated to video, logged in `Open_Issues.md`).

**The demo animatic exists**: `static/video/animatic_<project_id>.mp4`, 23.87s, 1920x1080, 30fps —
six Flow clips, Aiden narration locked per scene, burned-in captions.

- `VideoProvider` ABC, `AssetVideoProvider`, `GeminiVeoProvider`, `LocalVideoProvider`, factory.
- ffmpeg utils (normalize / probe / extract-last-frame); ffmpeg 8.1.2 is installed and on PATH.
- Launcher Settings persists `gemini_api_key`, `veo_model`, `video_provider`.
- Gemini config hardened beyond the original plan: `generate_audio=False`, `resolution=1080p`,
  `person_generation=allow_adult`, `negative_prompt`, and `reference_images` for character
  consistency. Poll deadline uses a monotonic clock.

**Veo API access is unconfirmed.** There is no free Veo tier on the Gemini API — it needs billing
enabled. A free read-only probe script exists to check whether a key can see Veo models without
spending anything. This is explicitly *not* on the demo critical path.

**Outstanding manual checkpoints from Plan 2:** CP3 (asset resolve), CP6 (launcher key UI), CP4 /
CP4b (real Veo calls — optional, costs money). See
`docs/superpowers/plans/2026-06-27-video-previs-02-engine-MANUAL-TESTS.md`.

---

## NEXT PRIORITIES

> **Superseded 2026-09-02:** Plan 4 was built ahead of Plan 3 and the demo animatic exists.
> The priorities below are re-ordered accordingly — Plan 5 (the Video tab) is now the critical
> path, and Plan 3 is deferred because the fixture already supplies ready clips.

### Priority 0 — Plan 5: Audio | Video tabbed studio (NOT YET WRITTEN)

The only remaining code between here and a full demo. Video preview, clip inspector, timeline
strip with reorder/trim/replace, subtitle toggle, and a Generate/Export button wired to
`POST /api/v1/projects/{id}/video/export` (which exists and works). Write the plan, then execute.

**If it slips, the demo still works** — play `static/video/animatic_<project_id>.mp4` directly
beside the existing audio studio and present the editor as the next increment. Protect rehearsal
time over UI completeness.

### Priority 1 — Plan 3: Orchestration (DEFERRED)

`docs/superpowers/plans/2026-09-02-video-previs-03-orchestration.md` — written, not started.
Art-direction LLM pass, clip provisioning, normalize-on-ingest, upload/asset endpoints,
provider-agnostic sequential generation with tail chaining, editor CRUD. Two manual checkpoints.

### Priority 2 — Plan 4: ffmpeg assembly — DONE 2026-09-02

`docs/superpowers/plans/2026-09-02-video-previs-04-assembly.md`, fully executed. Timeline fitting,
ASS captions, trim/freeze-pad primitives, `assemble`/`assemble_project`, and the export endpoint.
The Make-A-Wish animatic is built and plays. Rebuild any time with:

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe scripts/assemble_demo.py
```

### Schedule risk

One plan left instead of three, so the remaining risk is concentrated in the frontend. The
assembly milestone is already banked, which was the point of building Plan 4 first — the demo has
a floor now regardless of how Plan 5 goes. Spend leftover time on rehearsal and the two content
items below, not on UI polish.

---

## DEMO PREP CHECKLIST (week of 2026-09-14)

Content work, separate from the code plans. Most of it gates on nothing and should happen early.

- [x] **Seeded happy-path campaign** — `Make-A-Wish (Demo)` on `admin@example.com`, six segments +
      six pending clips with shot prompts. Rebuild with
      `backend/scripts/seed_makeawish_demo.py --reset`.
- [x] **Narration generated** with the Aiden preset.
- [x] **Generate the six Flow clips** — `documentation/Demo_MakeAWish_Brief.md` has paste-ready
      prompts. Six shots exceeds one day of free Flow credits, so **start early**; this is the real
      gate on demo material, not the code.
- [ ] **Pre-baked voice clone of Caleb** for a second example campaign, so cloning is demonstrated
      from a finished artifact rather than performed live.
- [ ] **Second live campaign** built in the room to show the emotion controls and per-segment
      direction working end to end. This is the "on the fly" half of the demo; the Make-A-Wish
      fixture is the pre-loaded half.
- [ ] **Watch the assembled animatic end to end** — frames, durations and streams are verified, but
      nobody has yet confirmed the read lands or that the scene 5-6 cut feels right at speed.
- [ ] **Rehearse once end to end** on the actual demo machine, in the network mode you'll present in.

Framing note: video previs is presented as a **stretch goal / WIP**, deliberately — it argues for
continued engagement. The provider-swap architecture is the credible-engineering half of that
pitch, and it is genuinely true: changing video backends is a config switch.

### Deferred — Tier 3 gaps (only if capacity appears, which it won't before the demo)

- Forgot-password / reset flow
- Per-segment mini waveforms in `ScriptEditor.tsx`
- Segment split
- "Regenerate All" arc-continuity fix (see `Open_Issues.md`)

---

## Session End Checklist

At end of session, update:
- `documentation/Project_Progress.md` — add the session entry
- `documentation/Open_Issues.md` — close resolved items, log new discoveries
- `documentation/Next_Session_Prompt.md` — set the next priorities
- Commit + push to `https://github.com/calebmfoster/Aria-Appeal`
