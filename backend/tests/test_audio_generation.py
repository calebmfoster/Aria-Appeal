import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.tts_engine import tts_service
import os

client = TestClient(app)

def test_tts_service_mock_generation():
    """
    Verifies that the TTSService generates a file in mock mode.
    """
    # Ensure mode is mock
    tts_service.mode = "mock"
    
    import asyncio
    file_path_url = asyncio.run(tts_service.generate_audio("Test text"))
    
    # Check if file exists in static/audio
    # URL is /static/audio/filename.wav
    filename = file_path_url.split("/")[-1]
    full_path = os.path.join(tts_service.output_dir, filename)
    
    assert os.path.exists(full_path)
    assert full_path.endswith(".wav")
    
    # Clean up
    if os.path.exists(full_path):
        os.remove(full_path)

@pytest.mark.asyncio
async def test_tts_service_qwen_local_fallback():
    """
    Verifies that if Qwen3 dependencies or weights are missing, it falls back to mock.
    """
    # Temporarily set mode to qwen-local and initialize
    tts_service.mode = "qwen-local"
    # Overwrite the path to something invalid to force a load failure if dependencies are present
    import app.core.config
    app.core.config.settings.QWEN_MODEL_PATH = "invalid-path-for-test"
    
    # Re-initialize
    tts_service._initialize_qwen()
    
    # After initialization fails, it should revert to mock mode
    assert tts_service.mode == "mock"
    
    # The generation should still work (via mock)
    file_path_url = await tts_service.generate_audio("Test text fallback")
    assert file_path_url.startswith("/static/audio/")
    
    filename = file_path_url.split("/")[-1]
    full_path = os.path.join(tts_service.output_dir, filename)
    assert os.path.exists(full_path)
    
    if os.path.exists(full_path):
        os.remove(full_path)

def test_generate_audio_endpoint():
    """
    Verifies the /api/v1/generate-audio endpoint accepts requests and returns a task ID.
    Note: This test mocks the Celery task delay to avoid running a worker info.
    """
    from unittest.mock import patch
    
    with patch("app.api.routes.audio.generate_audio_task.delay") as mock_task:
        mock_task.return_value.id = "test-task-id"
        
        response = client.post(
            "/api/v1/generate-audio",
            json={"text": "Hello world", "emotion": "happy"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-id"
        assert data["status"] == "PENDING"
