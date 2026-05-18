import asyncio
import httpx
from typing import Optional

async def test_audio():
    async with httpx.AsyncClient() as client:
        print('Testing generate-audio with custom string')
        res = await client.post('http://localhost:8000/api/audio/generate-audio', json={
            'text': 'Hello this is a test from the backend generator',
            'voice_profile_id': 'poe',
            'emotion': ''
        })
        print(res.status_code, res.text)
        
try:
    asyncio.run(test_audio())
except Exception as e:
    print('Could not connect to localhost:8000. Is the server running?', e)
