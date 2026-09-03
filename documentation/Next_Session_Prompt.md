# Next Session Prompt: Video Previsualization — Plan 3 (Orchestration)

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

**Plan 2 (video engine) is fully coded** on `feat/video-previs` — 31 video tests pass.

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

### Priority 1 — Plan 3: Orchestration

`docs/superpowers/plans/2026-09-02-video-previs-03-orchestration.md` — written, not started.
Art-direction LLM pass, clip provisioning, normalize-on-ingest, upload/asset endpoints,
provider-agnostic sequential generation with tail chaining, editor CRUD. Two manual checkpoints.

### Priority 2 — Plan 4: ffmpeg assembly (NOT YET WRITTEN)

The demo's payoff: fit clips to narration beats (freeze-last-frame padding), concat, mux master
narration, burn ASS subtitles, output MP4. Write this plan after Plan 3's Checkpoint A proves a real
Flow clip survives ingest.

### Priority 3 — Plan 5: Audio | Video tabbed studio (NOT YET WRITTEN)

Video preview, clip inspector, timeline strip with reorder/trim/replace, subtitle toggle.

### Schedule risk

Plans 3, 4 and 5 in ten working days is tight, and **Plan 5 (the UI) is the piece most likely to
slip.** Mitigation: Plan 4 produces a standalone MP4 through the API alone. If the Video tab isn't
ready, the demo still works — play the assembled MP4 next to the existing, fully-featured audio
studio and present the editor as the next increment. Protect the assembly milestone over the UI.

---

## DEMO PREP CHECKLIST (week of 2026-09-14)

Content work, separate from the code plans. Most of it gates on nothing and should happen early.

- [x] **Seeded happy-path campaign** — `Make-A-Wish (Demo)` on `admin@example.com`, six segments +
      six pending clips with shot prompts. Rebuild with
      `backend/scripts/seed_makeawish_demo.py --reset`.
- [x] **Narration generated** with the Aiden preset.
- [ ] **Generate the six Flow clips** — `documentation/Demo_MakeAWish_Brief.md` has paste-ready
      prompts. Six shots exceeds one day of free Flow credits, so **start early**; this is the real
      gate on demo material, not the code.
- [ ] **Pre-baked voice clone of Caleb** for a second example campaign, so cloning is demonstrated
      from a finished artifact rather than performed live.
- [ ] **Second live campaign** built in the room to show the emotion controls and per-segment
      direction working end to end. This is the "on the fly" half of the demo; the Make-A-Wish
      fixture is the pre-loaded half.
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
