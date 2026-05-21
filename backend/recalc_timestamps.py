"""One-shot script: recalculate start_time_ms / end_time_ms for all projects.

Run from backend/ with:
    python recalc_timestamps.py

Reads .env automatically for DATABASE_URL.
"""
import asyncio
import os
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

AUDIO_DIR = os.environ.get(
    "STATIC_AUDIO_DIR",
    str(Path(__file__).parent / "static" / "audio"),
)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy.future import select

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_async_engine(DATABASE_URL, echo=False, connect_args={"statement_cache_size": 0})
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)


def _duration_ms(audio_url: str) -> int:
    import soundfile as sf
    filename = audio_url.split("/")[-1]
    path = os.path.join(AUDIO_DIR, filename)
    try:
        return int(sf.info(path).duration * 1000)
    except Exception:
        return 0


async def recalc_all():
    import app.models.user  # noqa: F401
    import app.models.voice_profile  # noqa: F401
    import app.models.script_segment  # noqa: F401
    from app.models.project import Project

    async with SessionLocal() as db:
        result = await db.execute(
            select(Project).options(selectinload(Project.segments))
        )
        projects = result.scalars().all()
        print(f"Found {len(projects)} projects")

        fixed = 0
        for project in projects:
            segs = sorted(project.segments, key=lambda s: s.sequence_order)
            cursor = 0
            changed = False
            for seg in segs:
                old_start = seg.start_time_ms
                old_end = seg.end_time_ms
                seg.start_time_ms = cursor
                if seg.audio_url:
                    dur = _duration_ms(seg.audio_url)
                    seg.end_time_ms = cursor + dur
                    cursor += dur
                else:
                    seg.end_time_ms = cursor
                if seg.start_time_ms != old_start or seg.end_time_ms != old_end:
                    changed = True
            total_ms = cursor
            seg_summary = ", ".join(
                f"{s.sequence_order}:{s.end_time_ms}ms" for s in segs
            )
            print(f"  [{project.title[:30]}] total={total_ms/1000:.1f}s  segs=[{seg_summary}]  changed={changed}")
            if changed:
                fixed += 1

        await db.commit()
        print(f"\nDone — updated {fixed}/{len(projects)} projects")


if __name__ == "__main__":
    asyncio.run(recalc_all())
