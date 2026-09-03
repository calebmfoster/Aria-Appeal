"""Seed the Make-A-Wish demo campaign — the pre-loaded happy path for the client demo.

Creates a project, six narration segments, a video brief (style + character sheet), and six
pending VideoClips carrying per-shot prompts. Spends nothing: no LLM call, no video API call.
Audio is opt-in via --with-audio because it runs the real TTS pipeline on the GPU.

MAYA IS FICTIONAL — an illustrative composite written for this demo, not a real wish recipient.
The copy deliberately contains no statistics; swap in real Make-A-Wish figures before using any
of this in front of the client if you want numbers.

Usage:
    cd "D:/Repo/Aria Appeal/backend"
    ./.venv/Scripts/python.exe scripts/seed_makeawish_demo.py --list-users
    ./.venv/Scripts/python.exe scripts/seed_makeawish_demo.py --user-email you@example.com
    ./.venv/Scripts/python.exe scripts/seed_makeawish_demo.py --reset          # rebuild from scratch
    ./.venv/Scripts/python.exe scripts/seed_makeawish_demo.py --with-audio     # also run TTS (slow)
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

import app.db.base  # noqa: F401  — registers every mapper before we query
from app.db.session import SessionLocal
from app.models.user import User
from app.models.project import Project, ProjectStatus
from app.models.script_segment import ScriptSegment
from app.models.video_clip import VideoClip, VideoSourceType, VideoClipStatus

PROJECT_TITLE = "Make-A-Wish (Demo)"
ASSETS_DIR = Path(__file__).resolve().parent.parent / "static" / "video" / "assets"

# Only Aiden and Ryan are native-English presets — see Open_Issues.md. A warm female
# narrator would need a cloned voice profile; set VOICE_PROFILE_ID below if you have one.
SPEAKER_PRESET = "Aiden"
VOICE_PROFILE_ID = None

STYLE_PROMPT = (
    "Warm 2D storybook illustration, soft gouache textures with visible paper grain, "
    "limited palette of butter yellow, deep navy and warm cream. Gentle hand-drawn line "
    "work. Picture-book, not 3D animation. Soft directional light, no harsh shadows."
)

CHARACTER_SHEET = (
    "MAYA, girl aged about 8, medium brown skin, dark curly hair. Wears a hand-made "
    "cardboard space helmet painted silver and a bright yellow knitted scarf in every "
    "shot. Small frame, big posture. Keep her at medium-to-wide framing; avoid tight "
    "facial close-ups, where generated video drifts most."
)

# Narration is cut to fit the ACTUAL generated clips, which total 24s — Flow's per-clip
# limits made every shot shorter than the 8s the script was originally written for.
# Budgets come from Aiden's measured rate of ~3 words/sec; each line is written a little
# UNDER its window, because narration overrunning means the picture runs out.
#
# (narration text, emotion, shot prompt, clip start ms, clip end ms)
SEGMENTS = [
    (
        "Four months in one room. When you're eight, the sky feels far away.",
        "reflective",
        "A small hospital room at dawn. Maya sits cross-legged on the bed in her cardboard "
        "space helmet, drawing stars on the fogged window with one finger. Slow push in.",
        0, 5000,
    ),
    (
        "Maya had a wish. To be an astronaut.",
        "hopeful",
        "The room dissolves around her into a hand-drawn starfield. She floats, scarf "
        "trailing behind her, reaching toward a distant planet. Slow drift upward.",
        5000, 8000,
    ),
    (
        "So we took her to the space center. The doors opened.",
        "warm",
        "Daylight. Maya walks through the tall glass doors of a space center, helmet under "
        "one arm, looking up at a full-size rocket model. Wide, low angle.",
        8000, 12000,
    ),
    (
        "Maya wasn't a patient anymore. She was a pilot.",
        "uplifting",
        "Maya in a launch simulator seat, helmet on, hands on the controls. Warm light "
        "washes over her as the screens glow. Slow orbit around the seat.",
        12000, 15400,
    ),
    (
        "A wish is when hope becomes something you can hold.",
        "sincere",
        "Maya outside at golden hour, arms wide, scarf streaming behind her, spinning. "
        "Adults out of focus behind her, laughing. Handheld warmth.",
        15400, 19400,
    ),
    (
        "Another child is waiting. Your gift reaches them today.",
        "urgent",
        "The yellow scarf hangs on a hook by the hospital window, the bed neatly made, "
        "morning light filling the empty room. Static, slow fade.",
        19400, 24000,
    ),
]


async def pick_user(db, email: str | None) -> User:
    if email:
        user = (await db.execute(select(User).where(User.email == email))).scalars().first()
        if not user:
            raise SystemExit(f"No user with email {email!r}. Run --list-users to see options.")
        return user
    user = (await db.execute(select(User).order_by(User.id))).scalars().first()
    if not user:
        raise SystemExit("No users in the database. Register one in the app first.")
    return user


async def list_users(db) -> None:
    users = (await db.execute(select(User).order_by(User.id))).scalars().all()
    if not users:
        print("No users found.")
        return
    print(f"{len(users)} user(s):")
    for u in users:
        print(f"  {u.email}")


async def find_existing(db, user_id):
    stmt = (
        select(Project)
        .where(Project.user_id == user_id, Project.title == PROJECT_TITLE)
        .options(selectinload(Project.segments), selectinload(Project.video_clips))
    )
    return (await db.execute(stmt)).scalars().first()


async def destroy(db, project: Project) -> None:
    await db.execute(delete(VideoClip).where(VideoClip.project_id == project.id))
    await db.execute(delete(ScriptSegment).where(ScriptSegment.project_id == project.id))
    await db.execute(delete(Project).where(Project.id == project.id))
    await db.commit()


async def seed(email: str | None, reset: bool, with_audio: bool, attach_clips: bool) -> None:
    async with SessionLocal() as db:
        user = await pick_user(db, email)
        existing = await find_existing(db, user.id)

        if existing and not reset:
            print(f"Demo campaign already exists for {user.email}.")
            print(f"  project_id : {existing.id}")
            print(f"  segments   : {len(existing.segments)}")
            print(f"  clips      : {len(existing.video_clips)}")
            print("\nRe-run with --reset to rebuild it from scratch.")
            # Fall through to audio: --with-audio must work on an already-seeded
            # project, which is the normal case once the fixture exists.
            if with_audio:
                await _run_audio(existing.id)
            return

        if existing:
            print(f"Removing existing demo campaign {existing.id}...")
            await destroy(db, existing)

        project = Project(
            user_id=user.id,
            title=PROJECT_TITLE,
            target_audience={
                "audience": "Existing mid-level donors, ages 40-65",
                "emotion": "hope",
                "cause": "Granting wishes to children with critical illnesses",
                "organization_name": "Make-A-Wish",
                "script_length": "45s",
                "messaging_strategy": "Single-story arc: confinement, imagination, wish "
                                      "granted, joy, ask. Hope-forward, never pity-forward.",
            },
            status=ProjectStatus.GENERATED,
            video_brief={"style_prompt": STYLE_PROMPT, "character_sheet": CHARACTER_SHEET},
            subtitle_style={"enabled": True, "font_size": 36, "position": "bottom", "color": "FFFFFF"},
        )
        db.add(project)
        await db.flush()

        for i, (text, emotion, shot, _start, _end) in enumerate(SEGMENTS):
            db.add(ScriptSegment(
                project_id=project.id,
                text=text,
                emotion=emotion,
                sequence_order=i,
                speaker_preset=SPEAKER_PRESET,
                voice_profile_id=VOICE_PROFILE_ID,
            ))
            await db.flush()

        await db.commit()

        stmt = select(ScriptSegment).where(
            ScriptSegment.project_id == project.id
        ).order_by(ScriptSegment.sequence_order)
        segments = (await db.execute(stmt)).scalars().all()

        attached = 0
        for i, (seg, (_, _, shot, start_ms, end_ms)) in enumerate(zip(segments, SEGMENTS), start=1):
            asset = f"maya_{i:02d}.mp4"
            have_asset = attach_clips and (ASSETS_DIR / asset).exists()
            if have_asset:
                attached += 1
            db.add(VideoClip(
                project_id=project.id,
                segment_id=seg.id,
                sequence_order=seg.sequence_order,
                source_type=VideoSourceType.ASSET if have_asset else VideoSourceType.GENERATED,
                status=VideoClipStatus.READY if have_asset else VideoClipStatus.PENDING,
                video_url=f"/static/video/assets/{asset}" if have_asset else None,
                prompt=shot,
                # Timeline positions from the real generated clips, so assembly has
                # ground truth to validate against before the editor exists.
                timeline_start_ms=start_ms,
                timeline_end_ms=end_ms,
                duration_ms=end_ms - start_ms,
            ))
        await db.commit()

        print("Seeded the Make-A-Wish demo campaign.")
        print(f"  user       : {user.email}")
        print(f"  project_id : {project.id}")
        print(f"  segments   : {len(segments)} (narration, no audio yet)")
        print(f"  clips      : {len(SEGMENTS)} total, {attached} attached from assets")
        print(f"\n  studio     : http://localhost:3000/studio/{project.id}")
        print("\nMaya is FICTIONAL — an illustrative composite, not a real wish recipient.")
        print("The copy contains no statistics by design; add real figures if you want numbers.")

    if with_audio:
        await _run_audio(project.id)
    else:
        print("\nNarration audio NOT generated. Re-run with --with-audio, or hit "
              "Regenerate in the studio.")


async def _run_audio(project_id) -> None:
    """Run the real chained TTS pipeline over the project's segments."""
    print("\nGenerating narration audio (real TTS on GPU, this takes a while)...")
    from app.api.routes.projects import _generate_baseline_audio_for_project
    await _generate_baseline_audio_for_project(project_id)
    print("Audio generation finished.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed the Make-A-Wish demo campaign.")
    ap.add_argument("--user-email", default=None, help="Owner; defaults to the first user.")
    ap.add_argument("--list-users", action="store_true", help="List users and exit.")
    ap.add_argument("--reset", action="store_true", help="Delete and rebuild if it exists.")
    ap.add_argument("--with-audio", action="store_true", help="Also run the TTS pipeline.")
    ap.add_argument("--attach-clips", action="store_true",
                    help="Wire maya_01..06.mp4 from static/video/assets in as READY clips.")
    args = ap.parse_args()

    if args.list_users:
        asyncio.run(_list_only())
        return
    asyncio.run(seed(args.user_email, args.reset, args.with_audio, args.attach_clips))


async def _list_only() -> None:
    async with SessionLocal() as db:
        await list_users(db)


if __name__ == "__main__":
    main()
