# Next Session Prompt: Demo Content + Rehearsal (all code is built, merged and live-tested)

Read `CLAUDE.md`, `documentation/Project_Progress.md`, `documentation/Open_Issues.md`, and
`documentation/Product_Roadmap.md` (Tier V) for full context.

---

## HARD DEADLINE

**Client demo to the CTO, CAO and CIO — week of 2026-09-14.** Four working days from 2026-09-08.

The audience is a technical/administrative buying committee, not a creative one. They will probe
architecture, vendor lock-in and cost model more than aesthetics, and have signalled they may want a
different video provider. Two rules follow:

1. **Build the demo on Flow-sourced / uploaded clips, never on live Veo.** No paid API dependency, no
   live generation call in the room. The `VideoProvider` abstraction means this costs us nothing
   architecturally — and provider-swappability is a selling point to say out loud.
2. **Pre-generate everything before the meeting.** Nothing generated live on stage.

---

## State

**`main` is the demo build.** `feat/video-previs` merged 2026-09-07 via PR #4 (merge commit
`7815f1d`) — 53 commits, the whole video feature plus the voice-preview work. Nothing is left on a
side branch.

Everything below the line is content and rehearsal. There is no code work left on the critical path.

Test state: backend `5 failed, 133 passed`; frontend `6 failed, 31 passed`. Both failure counts are
the documented stale sets — see `Open_Issues.md`. Run `pytest tests/` (not bare `pytest`) and
`npx jest` (there is no `npm test` script).

---

## Priority 0 — Listen to what we have

Nobody has actually listened to any of this end to end. It is the cheapest remaining risk and it is
human-only work.

- [ ] **Watch the assembled animatic end to end.** Frames, durations and streams are verified
      mechanically, but nobody has confirmed the read lands or that the scene 5→6 cut feels right at
      speed.
- [ ] **Listen to the nine preset previews** in `backend/static/audio/preview_preset_*.wav`. They
      are all real speech, but the CJK reads are unverified. `Uncle_Fu` takes 4.65s for the same
      Chinese line the other Chinese presets deliver in ~1.9s — check that one first. Fix direction
      if a read is bad is in `Open_Issues.md`.
- [ ] **Listen to the cloned "Me" preview** and confirm it sounds like the source voice.

## Priority 1 — Remaining demo content

- [ ] **Pre-baked voice clone of Caleb** for a second example campaign, so cloning is demonstrated
      from a finished artifact rather than performed live.
- [ ] **Second live campaign** built in the room to show the emotion controls and per-segment
      direction working end to end. This is the "on the fly" half of the demo; the Make-A-Wish
      fixture is the pre-loaded half.
- [ ] **Decide whether to show the multi-language voices.** They are a genuine differentiator for a
      nonprofit serving diverse communities, but be straight about the boundary: the *voice* layer
      covers English, Chinese, Japanese and Korean. Scripts, UI and subtitles are English-only. Say
      "multi-language narration", not "multi-language product" — the gap is easy to probe.

## Priority 2 — Rehearse

- [ ] **Rehearse once end to end on the actual demo machine**, in the network mode you'll present in.
      Note the frontend's `.env.local` points at a Tailscale IP (`100.72.140.26:8000`), so the
      backend must be started with `--host 0.0.0.0`, not the default loopback bind, or the browser
      gets `ERR_CONNECTION_REFUSED`.
- [ ] **Pre-warm before the meeting** so nothing synthesizes on stage:
      ```bash
      cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe scripts/warm_voice_previews.py
      ```
- [ ] **Sanity-check the merged build once** — the merge was clean, but the demo has never been run
      from a `main` checkout. Start it fresh from `main` and click through both campaigns.

---

## Open judgement call (not a bug)

The user must still notice the amber "out of date" banner and click **Re-assemble** after editing a
script. Audio auto-re-exports; video does not. Auto-triggering video re-assembly is possible but
assembly is slow and GPU/ffmpeg-bound, so an automatic rebuild on every edit may be worse than the
prompt. Current decision: **leave the banner**, it is the safer behaviour on stage.

## Deferred — not before the demo

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
