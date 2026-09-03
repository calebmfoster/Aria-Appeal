# Design Spec — Audio | Video Studio (Plan 5)

**Date:** 2026-09-02
**Status:** approved
**Context:** Final piece before the client demo to the CTO, CAO and CIO, week of 2026-09-14.
**Builds on:** the Phase 1 spec (`2026-06-26-video-previsualization-design.md`), Plan 2 (providers),
Plan 4 (assembly + export endpoint, both built and working).

---

## Goal

Let a campaign that has video show its assembled animatic inside the studio, and let a campaign
that doesn't carry on exactly as it does today.

## The question this answers

Does adding video fundamentally change the app's look and flow? **No — and it shouldn't.**

Two non-AI tools solve this same manual loop. [Boords](https://boords.com/animatic-software) turns
storyboard panels into a timed animatic in one click, with uploaded voiceover, subtitles, and edits
that propagate automatically. [Descript](https://www.descript.com/video-editing) — which this app
already imitates for audio — edits video *by editing the transcript*, with the timeline demoted to a
secondary view.

Both point the same way: **the script is already the timeline.** Aria Appeal's segments are
simultaneously the transcript, the shot list, and the storyboard panels. A traditional NLE would
introduce a second, competing metaphor for the same underlying data. So the Video tab reuses the
studio's existing three-column shell and swaps what sits in the middle.

Rejected alternatives: a Boords-style panel grid (reads as storyboarding rather than editing, and
breaks the shared shell), and a Premiere-style track timeline (the scope trap — the Phase 1 spec
already defers free multi-track editing to Phase 2).

---

## Campaign medium — audio-only vs audio + video

Not every campaign wants video. Radio spots and phone appeals are audio deliverables, and a large
share of nonprofit media buying is exactly that.

**`target_audience.medium`** = `"audio"` | `"video"`, stored in the existing JSON column. No
migration: the key's absence means `"audio"`, so every existing campaign is untouched and no
already-recorded radio spot sprouts a video tab it can never fill.

- **Audio-only:** the studio renders exactly as it does today. **No tab bar at all** — not a
  disabled tab, not an empty state. Nothing changes for these users.
- **Audio + video:** the studio grows an `Audio | Video` toggle.

Set at campaign creation (a toggle in the creation modal, defaulting to audio) and changeable later
from the studio, so an audio campaign can gain video without being recreated. Dashboard campaign
cards carry a small medium badge.

A `Project.medium` column would be cleaner long-term; the JSON field is the deadline-appropriate
choice and migrates trivially later.

---

## Layout

The Video tab reuses the shell: 30% script / 45% stage / 25% inspector, under the existing header.

**Left — segment list.** The same rows, each gaining a poster frame and a clip status dot. The
poster is a muted, preloaded `<video>` pointed at the clip URL, so the browser renders the first
frame and no thumbnail generation is needed on the backend. Clicking a segment seeks the preview,
mirroring how clicking currently seeks the waveform.

**Centre — preview.** A `<video>` playing the assembled animatic, with a thin clip strip beneath
showing the shots in order with durations, current one highlighted. Before the first assembly, a
single "Assemble video" button.

**Right — inspector.** The selected clip, read-only: shot prompt, source badge, duration, timeline
position. Below it, collapsible project-level detail — the visual bible (style prompt and character
sheet) and the subtitle control.

## Scope — preview and export only

Reorder, trim, replace, per-clip regenerate, and editable shot prompts are **out of scope**. They
need Plan 3's endpoints, which aren't built, and they roughly double the frontend work. The smallest
thing that proves the loop leaves room for rehearsal and the remaining content work.

The one control that writes is the subtitle toggle and font size, because it changes the next
export. It must read as **"applies on next assembly"** rather than appearing to affect the current
video live.

## Export flow

The header's export button becomes contextual: "Export & Download" on Audio, "Assemble video" on
Video. It POSTs to `/api/v1/projects/{id}/video/export`, polls the GET every two seconds, and swaps
the player source when status flips to `ready`. Failure surfaces the error string the endpoint
already returns.

## Backend addition

One endpoint: **`GET /api/v1/projects/{id}/video/clips`** returning clips ordered by
`sequence_order` plus `video_brief` and `subtitle_style`. This is a slice of Plan 3's Task 6, roughly
fifteen lines, and it does not pull the rest of Plan 3 in.

Also needed: a way to persist `medium` and `subtitle_style`. Extend the existing project PATCH rather
than adding a new route.

## State

`studioStore` gains `activeTab`, `videoClips`, `videoExport` (status, url, error), and `medium`,
following the existing slice pattern.

## Error handling

- Assembly failure shows the endpoint's error string with a retry, and leaves any previous animatic
  playable.
- Clips not ready gives the endpoint's message naming the offending scenes.
- A missing animatic file falls back to the empty state rather than a broken player.

## Testing

Component tests for the tab toggle (absent on audio-only campaigns), the clip strip ordering, and
the export polling state machine — following the existing `ScriptEditor.test.tsx` and
`InspectorPanel.test.tsx` patterns. Backend test for the new list endpoint, including cross-user 404.

## Known risk

**Playback teardown.** `WaveformVisualizer`'s unmount-stops-playback fix (session 12) must be
mirrored on the video element and on tab switching, or leaving the studio — or flipping to the Audio
tab — leaves video audio playing. This is the exact bug already fixed once for audio.

## Success criteria

- An audio-only campaign is visually and behaviourally identical to today.
- A video campaign shows `Audio | Video`, and the Video tab plays the assembled animatic with
  narration and burned-in captions.
- Assembly can be triggered and its progress followed from the studio.
- Switching tabs or leaving the studio stops playback.
