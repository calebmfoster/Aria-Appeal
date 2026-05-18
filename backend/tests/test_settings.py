import sys
import os
import json
from fastapi.testclient import TestClient

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.core.system_config import config_manager

client = TestClient(app)

def test_settings_api():
    print("Testing Settings API...")

    # 1. Get initial settings
    response = client.get("/api/v1/settings")
    assert response.status_code == 200
    initial_settings = response.json()
    print(f"Initial Settings: {initial_settings}")

    # 2. Update settings
    new_settings = initial_settings.copy()
    new_settings["llm_provider"] = "openai"
    new_settings["llm_model"] = "gpt-4o"

    response = client.post("/api/v1/settings", json=new_settings)
    assert response.status_code == 200
    updated_responses = response.json()
    assert updated_responses["llm_provider"] == "openai"
    assert updated_responses["llm_model"] == "gpt-4o"
    print("SUCCESS: Settings updated via API.")

    # 3. Verify persistence (mocking file check by checking manager state)
    current_config = config_manager.get_settings()
    assert current_config.llm_provider == "openai"
    print("SUCCESS: ConfigManager state updated.")

    # 4. Revert settings for cleanup
    client.post("/api/v1/settings", json=initial_settings)
    print("Cleanup: Settings reverted.")

if __name__ == "__main__":
    try:
        test_settings_api()
        print("ALL TESTS PASSED")
    except Exception as e:
        print(f"FAILED: {e}")
        exit(1)
