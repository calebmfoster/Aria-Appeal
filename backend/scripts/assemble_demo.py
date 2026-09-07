"""Assemble a project's animatic from the command line.

Runs the same code path the export endpoint will, so the demo artifact and the
product are never two different things.

Usage:
    cd "D:/Repo/Aria Appeal/backend"
    ./.venv/Scripts/python.exe scripts/assemble_demo.py
    ./.venv/Scripts/python.exe scripts/assemble_demo.py --title "Make-A-Wish (Demo)"
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

import app.db.base  # noqa: F401
from app.db.session import SessionLocal
from app.models.project import Project
from app.services.video import ffmpeg_utils
from app.services.video.assembly import assemble_project

DEFAULT_TITLE = "Make-A-Wish (Demo)"


async def main(title: str) -> None:
    async with SessionLocal() as db:
        project = (await db.execute(
            select(Project).where(Project.title == title)
        )).scalars().first()
        if project is None:
            raise SystemExit(f"No project titled {title!r}.")

        print(f"Assembling {project.title} ({project.id})...")
        url = await assemble_project(db, project.id)

        from app.services.video.assembly import static_root
        path = os.path.join(static_root(), "video", os.path.basename(url))
        dur = ffmpeg_utils.probe_duration_ms(path)
        info = ffmpeg_utils.probe_stream_info(path)
        size_mb = os.path.getsize(path) / (1024 * 1024)

        print(f"\n  {url}")
        print(f"  {path}")
        print(f"  {dur / 1000:.2f}s  {info['width']}x{info['height']}  "
              f"{info['fps']:.1f}fps  audio={info['has_audio']}  {size_mb:.1f} MB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default=DEFAULT_TITLE)
    args = ap.parse_args()
    asyncio.run(main(args.title))
