# Demo Creative Brief — Make-A-Wish (Test Client)

Companion to `backend/scripts/seed_makeawish_demo.py`, which loads all of this into the database.
Paste the prompts below into Google Flow to produce the clips.

> **Maya is fictional** — an illustrative composite written for this demo, not a real wish
> recipient. The copy contains **no statistics** by design; every number in a real Make-A-Wish
> campaign should come from the client. Do not generate or reproduce Make-A-Wish logos, the star
> mark, or any brand asset — the name belongs in narration and slides, not in generated frames.

---

## Why animated, not photoreal

Three reasons, in order of how much they matter:

1. **Consistency.** Generated video drifts between shots. Drift on an illustrated character reads
   as style; drift on a photoreal human face reads as uncanny. This is the single biggest technical
   risk in the feature, and art direction is the cheapest mitigation.
2. **Honesty about the artifact.** This is previsualization — an animatic for pitching, not a
   finished spot. A storybook look sets that expectation. Photoreal invites "why isn't this done?"
3. **Taste.** An obviously-illustrated child carries no implication that a real patient was
   depicted or synthesized. That matters when the audience is the organization that serves them.

**The consistency trick:** hold identity with a *costume anchor*, not a face. The silver cardboard
helmet and yellow scarf survive shot-to-shot drift; facial features will not. Keep framing
medium-to-wide and avoid tight close-ups.

---

## Visual bible

Maps to `Project.video_brief`. Paste into Flow's style field, or prepend to each prompt.

**Style prompt**
```
Warm 2D storybook illustration, soft gouache textures with visible paper grain, limited palette
of butter yellow, deep navy and warm cream. Gentle hand-drawn line work. Picture-book, not 3D
animation. Soft directional light, no harsh shadows.
```

**Character sheet**
```
MAYA, girl aged about 8, medium brown skin, dark curly hair. Wears a hand-made cardboard space
helmet painted silver and a bright yellow knitted scarf in every shot. Small frame, big posture.
Keep her at medium-to-wide framing; avoid tight facial close-ups.
```

---

## Six shots

Arc: confinement → imagination → wish granted → joy → resonance → ask.

**Narration was cut roughly in half after the footage came back.** Flow's per-clip limits produced a
23.85s film, not the ~45s the script was written for, so every line is rewritten to fit its actual
scene window. Measured against Aiden, all six now fit with 2.95s of total slack.

| # | Window | Narration | Read | Emotion | Shot prompt |
|---|---|---|---|---|---|
| 1 | 0–5.0s | Four months in one room. When you're eight, the sky feels far away. | 4.8s | reflective | A small hospital room at dawn. Maya sits cross-legged on the bed in her cardboard space helmet, drawing stars on the fogged window with one finger. Slow push in. |
| 2 | 5.0–8.0s | Maya had a wish. To be an astronaut. | 2.7s | hopeful | The room dissolves around her into a hand-drawn starfield. She floats, scarf trailing behind her, reaching toward a distant planet. Slow drift upward. |
| 3 | 8.0–12.0s | So we took her to the space center. The doors opened. | 2.8s | warm | Daylight. Maya walks through the tall glass doors of a space center, helmet under one arm, looking up at a full-size rocket model. Wide, low angle. |
| 4 | 12.0–15.4s | Maya wasn't a patient anymore. She was a pilot. | 3.1s | uplifting | Maya in a launch simulator seat, helmet on, hands on the controls. Warm light washes over her as the screens glow. Slow orbit around the seat. |
| 5 | 15.4–19.4s | A wish is when hope becomes something you can hold. | 3.2s | sincere | Maya outside at golden hour, arms wide, scarf streaming behind her, spinning. Adults out of focus behind her, laughing. Handheld warmth. |
| 6 | 19.4–24.0s | Another child is waiting. Your gift reaches them today. | 4.2s | urgent | Maya stands in the field and looks up. The sky fades from golden hour to night, and a shooting star crosses it. Static, slow fade. |

Shot 6 carries the ask emotionally; the narration does the literal work. Medical context stays
implied throughout — never depicted.

### Writing to a time budget with Aiden

Aiden's pace is **not** a stable words-per-second — it is driven by sentence breaks, because each
period buys a pause. Measured on this script: scene 3 ran 11 words in 2.9s (3.8 w/s) while the first
cut of scene 6 took 13 words in 5.7s (2.3 w/s), purely because scene 6 had three sentences. When a
line must fit a tight window, **join clauses with commas rather than splitting into sentences** —
that saves more time than deleting words.

### RESOLVED — scene 6 no longer reads as a death

The original scene 6 was an empty hospital bed with the scarf left on a hook. That is ambiguous: a
viewer can read it as Maya having died, which is a serious risk in front of an organization serving
children with critical illnesses. **Replaced 2026-09-02** with Maya alive in the field, looking up as
the sky fades to night and a shooting star crosses it.

The replacement is better than a fix. It bookends scene 2's starfield, the shooting star carries the
wish metaphor without stating it, and the final frames are open sky — clean real estate for a logo
and donate CTA in a finished spot, which is worth pointing out in the room.

Kept as a record because it generalizes: when the tool generates an ending on an absence, check what
the absence implies. That judgment is the human-in-the-loop step the product is built around.

---

## Source footage — NOT IN GIT

`backend/static/video/` is gitignored, so the demo clips exist **only on this machine**. Back them
up somewhere before demo day; losing them means regenerating six shots on daily-limited credits.

Current state: the delivered pitch film (`MAW pitch.mp4`, 23.85s, 1280x720, ~24fps) was split at the
scene boundaries into `backend/static/video/assets/maya_01.mp4` … `maya_06.mp4`, audio stripped.
`--attach-clips` wires those onto the seeded clip rows as `ASSET` / `READY`.

Note the source is **720p**, while `ffmpeg_utils.TARGET_W/H` normalizes to 1920x1080 — that would
upscale and soften every frame for no gain. Since all demo material is 720p, drop the target to
1280x720 when Plan 4 lands.

## Producing the clips

1. Generate shots 1-6 in Flow with the style prompt applied to each. Free daily credits cover a few
   per day, so start early — six shots is more than one day's allowance.
2. Prefer Flow's reference-image / scene-extension tooling to carry Maya between shots.
3. Download each as mp4. Name them `maya_01.mp4` … `maya_06.mp4`.
4. Drop them in `backend/static/video/assets/`.
5. Once Plan 3 Task 4 lands, upload them onto the seeded clips through the API; before then they
   sit ready in the assets dir.

Regenerate any shot where Maya reads as a different child. That judgment — which takes are usable —
is exactly the human-in-the-loop step the product is designed around, and worth saying out loud in
the room.

---

## Narration voice

The seed stamps **Aiden** on every segment. Only Aiden and Ryan are native-English presets (see
`Open_Issues.md`); there is **no native-English female preset**, so a female narrator for this
script requires a cloned voice profile. If a warm female read is wanted for the demo, clone one and
set `VOICE_PROFILE_ID` in the seed script before running it.

---

## Reseeding

```bash
cd "D:/Repo/Aria Appeal/backend" && ./.venv/Scripts/python.exe scripts/seed_makeawish_demo.py --user-email admin@example.com --reset
```

Add `--with-audio` to run the real TTS pipeline and produce narration. It is slow (GPU) but should
be done well before demo day, not on it.
