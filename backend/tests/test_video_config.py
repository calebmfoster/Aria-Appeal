from app.core.system_config import SystemSettings


def test_video_settings_defaults():
    s = SystemSettings()
    assert s.video_provider == "gemini"
    assert s.gemini_api_key == ""
    assert s.veo_model == "veo-3.0-generate-001"


def test_video_settings_roundtrip_json():
    s = SystemSettings(gemini_api_key="abc123", video_provider="gemini")
    dumped = s.model_dump_json()
    restored = SystemSettings.model_validate_json(dumped)
    assert restored.gemini_api_key == "abc123"
    assert restored.video_provider == "gemini"
