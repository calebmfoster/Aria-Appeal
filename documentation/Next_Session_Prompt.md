# Next Session Prompt: Demo Rehearsal + Content (all planned code is built and live-tested)

Read `CLAUDE.md`, `documentation/Project_Progress.md`, `documentation/Open_Issues.md`, and
`documentation/Product_Roadmap.md` (Tier V) for full context.

---

## HARD DEADLINE

**Client demo to the CTO, CAO and CIO — week of 2026-09-14.** Roughly seven working days from
2026-09-03.

The audience is a technical/administrative buying committee, not a creative one. They will probe
architecture, vendor lock-in and cost model more than aesthetics, and have signalled they may want a
different video provider. Two rules follow:

1. **Build the demo on Flow-sourced / uploaded clips, never on live Veo.** No paid API dependency, no
   live generation call in the room. The `VideoProvider` abstraction means this costs us nothing
   architecturally — and provider-swappability is a selling point to say out loud.
2. **Pre-generate everything before the meeting.** Nothing generated live on stage.

---

## Session 15 (2026-09-04) — live testing pass

Caleb drove the studio himself. Everything in the Video tab and the voice pickers checked out
except two things, both now fixed and verified:

- **A re-assembled animatic never appeared.** Assembly worked the whole time (the MP4 grew 23.87s →
  24.37s with the new lines) — the player just never reloaded it, because the animatic URL is
  identical on every assembly. Now cache-busted and keyed on an assembly stamp.
- **Nothing flagged a stale animatic.** Audio auto-re-exports after a regenerate; video does not,
  and still reported `ready`. Assembly now fingerprints its inputs and the Video tab shows an amber
  "out of date — re-assemble" banner. Won't fire on an animatic built before this existed; it
  self-heals on the next assembly.
- Plus an `AbortError` on every tab switch (uncaught WaveSurfer `load()` rejection) — silenced,
  verified 0 unhandled rejections across 12 switches.

**Known rough edge worth deciding on:** the user still has to notice the banner and click
Re-assemble. Consider auto-triggering video re-assembly after a regenerate the way audio does — but
assembly is slow and GPU/ffmpeg-bound, so an automatic rebuild on every edit may be worse than the
prompt. Judgement call, not a bug.

## State after Session 14 (2026-09-03)

**Every planned code item for the demo is built.** Plans 2, 4 and 5 are executed on
`feat/video-previs`. Plan 3 remains deliberately unexecuted — the seeded fixture already supplies
ready clips, so it is off the critical path.

**The studio has a working Audio | Video tab.** Verified in the running app, not just in tests:

- `Make-A-Wish (Demo)` shows `Audio | Video`; the Video tab plays the 23.87s animatic with
  narration and burned-in captions.
- Clicking Scene 4 seeks the player to exactly 12.0s; clip-strip item 6 to 19.4s.
- Playback stops on tab switch and on leaving the studio.
- `Alzheimer's Awareness` (audio-only) renders with **zero** tab elements and the original
  Export/Download header — visually and behaviourally identical to before.

**Voice previews work.** Cloned voices synthesize a 1.56s greeting instead of replaying the user's
52.8s uploaded reference; all nine presets are exposed, grouped by language, each previewing in its
own language. All nine preset previews are pre-generated and cached.

**Test state:** backend `5 failed, 126 passed`; frontend `6 failed, 27 passed`. Both failure counts
are the documented stale sets — see `Open_Issues.md`. Run `pytest tests/` (not bare `pytest`) and
`npx jest` (there is no `npm test` script).

---

## NEXT PRIORITIES — content and rehearsal, not code

The remaining risk is no longer in the codebase. Spend the time on the material and the run-through.

### Priority 0 — Listen to what we have

Nobody has actually listened to any of this end to end. It is the cheapest remaining risk.

- [ ] **Watch the assembled animatic end to end.** Frames, durations and streams are verified
      mechanically, but nobody has confirmed the read lands or that the scene 5→6 cut feels right at
      speed.
- [ ] **Listen to the nine preset previews** in `backend/static/audio/preview_preset_*.wav`. They
      are all real speech, but the CJK reads are unverified. `Uncle_Fu` takes 4.65s for the same
      Chinese line the other Chinese presets deliver in ~1.9s — check that one first. Fix direction
      if a read is bad is in `Open_Issues.md`.
- [ ] **Listen to the cloned "Me" preview** and confirm it sounds like the source voice.

### Priority 1 — Remaining demo content

- [ ] **Pre-baked voice clone of Caleb** for a second example campaign, so cloning is demonstrated
      from a finished artifact rather than performed live.
- [ ] **Second live campaign** built in the room to show the emotion controls and per-segment
      direction working end to end. This is the "on the fly" half of the demo; the Make-A-Wish
      fixture is the pre-loaded half.
- [ ] **Decide whether to show the multi-language voices.** They are a genuine differentiator for a
      nonprofit serving diverse communities, but be straight about the boundary: the *voice* layer
      covers English, Chinese, Japanese and Korean. Scripts, UI and subtitles are English-only. Say
      "multi-language narration", not "multi-language product" — the gap is easy to probe.

### Priority 2 — Rehearse

- [ ] **Rehearse once end to end on the actual demo machine**, in the network mode you'll present in.
      Note the frontend's `.env.local` points at a Tailscale IP (`100.72.140.26:8000`), so the
      backend must be started with `--host 0.0.0.0`, not the default loopback bind, or the browser
      gets `ERR_CONNECTION_REFUSED`.
- [ ] **Pre-warm before the meeting** so nothing synthesizes on stage:
      ```bash
      cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe scripts/warm_voice_previews.py
      ```

### Priority 3 — Merge the branch

`feat/video-previs` is a long-running branch carrying the whole video feature and is now demoable.
Consider merging to `main` before the demo so the presented build is the mainline build.

### Deferred — not before the demo

- **Plan 3 — Orchestration.** `docs/superpowers/plans/2026-09-02-video-previs-03-orchestration.md`,
  written and not started. Art-direction LLM pass, clip provisioning, upload/asset endpoints,
  provider-agnostic sequential generation with tail chaining, editor CRUD. Unlocks the Video tab's
  out-of-scope half: reorder, trim, replace, per-clip regenerate, editable shot prompts.
- Delete or relocate `backend/test_celery_task.py` (breaks bare `pytest`).
- Rewrite or delete the 5 stale backend tests and the 6 stale frontend tests.
- Forgot-password / reset flow; per-segment mini waveforms; segment split; the "Regenerate All"
  arc-continuity fix.

---

## Framing note

Video previs is presented as a **stretch goal / WIP**, deliberately — it argues for continued
engagement. The provider-swap architecture is the credible-engineering half of that pitch, and it is
genuinely true: changing video backends is a config switch. The Video tab is honest about its own
limits too — it previews and exports; it does not yet edit.

---

## Session End Checklist

At end of session, update:
- `documentation/Project_Progress.md` — add the session entry
- `documentation/Open_Issues.md` — close resolved items, log new discoveries
- `documentation/Next_Session_Prompt.md` — set the next priorities
- Commit + push to `https://github.com/calebmfoster/Aria-Appeal`
