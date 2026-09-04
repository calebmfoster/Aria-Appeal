"""Pre-generate the nine preset voice previews so the pickers never stall.

Run before a demo:
    cd "D:/Repo/Aria Appeal/backend"
    ./.venv/Scripts/python.exe scripts/warm_voice_previews.py

Add --force to regenerate previews that are already cached.
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# The greetings are Chinese/Japanese/Korean and the Windows console defaults to
# cp1252, which raises on them mid-run. Replace rather than crash.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from app.services import voice_preview  # noqa: E402
from app.services.voice_presets import PRESETS  # noqa: E402


async def main(force: bool) -> int:
    failures = 0
    for preset in PRESETS:
        filename = voice_preview.preset_preview_filename(preset.speaker)
        if force:
            path = os.path.join(voice_preview.tts_service.output_dir, filename)
            if os.path.isfile(path):
                os.remove(path)

        print(f"{preset.speaker:<10} [{preset.language_label}] {preset.greeting}")
        url = await voice_preview.ensure_preset_preview(preset.speaker)
        if url:
            print(f"           -> {url}")
        else:
            print("           -> FAILED")
            failures += 1

    print(f"\n{len(PRESETS) - failures}/{len(PRESETS)} previews ready.")
    return 1 if failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="regenerate cached previews")
    raise SystemExit(asyncio.run(main(parser.parse_args().force)))
