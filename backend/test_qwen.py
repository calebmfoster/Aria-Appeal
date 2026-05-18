import asyncio
import os
import sys

# Add the current directory to sys.path so app can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.tts_engine import tts_service

async def main():
    try:
        # Let's pass a random UUID string to simulate what the frontend passes
        res = await tts_service.generate_audio("This is a voice test.", voice_profile_id="00000000-0000-0000-0000-000000000000", emotion="happy")
        print("GENERATED SUCCESSFULLY:", res)
    except Exception as e:
        print("CRASH REASON:", e)

if __name__ == "__main__":
    asyncio.run(main())
