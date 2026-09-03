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

Arc: confinement → imagination → wish granted → joy → resonance → ask. Roughly 8s each, ~45s total.

| # | Narration | Emotion | Shot prompt |
|---|---|---|---|
| 1 | When you're eight years old, and you've spent four months inside the same room, the sky starts to feel very far away. | reflective | A small hospital room at dawn. Maya sits cross-legged on the bed in her cardboard space helmet, drawing stars on the fogged window with one finger. Slow push in. |
| 2 | But Maya had a wish. Not to be better someday. To be an astronaut now, this year, while it still felt possible. | hopeful | The room dissolves around her into a hand-drawn starfield. She floats, scarf trailing behind her, reaching toward a distant planet. Slow drift upward. |
| 3 | So we took her to the space center. Doors she had only ever seen in books opened, and she walked straight through them. | warm | Daylight. Maya walks through the tall glass doors of a space center, helmet under one arm, looking up at a full-size rocket model. Wide, low angle. |
| 4 | She flew a launch simulation. Hands steady on the controls. For a few minutes, Maya wasn't a patient. She was a pilot. | uplifting | Maya in a launch simulator seat, helmet on, hands on the controls. Warm light washes over her as the screens glow. Slow orbit around the seat. |
| 5 | Wishes aren't a distraction from treatment. Families tell us they are the moment hope turns into something a child can hold onto. | sincere | Maya outside at golden hour, arms wide, scarf streaming behind her, spinning. Adults out of focus behind her, laughing. Handheld warmth. |
| 6 | There is another child waiting for their wish right now. Your gift is what reaches them. Please give today. | urgent | The yellow scarf hangs on a hook by the hospital window, the bed neatly made, morning light filling the empty room. Static, slow fade. |

Shot 6 carries the ask emotionally; the narration does the literal work. Medical context stays
implied throughout — never depicted.

---

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
