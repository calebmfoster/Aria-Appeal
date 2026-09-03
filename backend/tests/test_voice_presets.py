from app.services.voice_presets import PRESETS, get_preset, ENGLISH_DEFAULT
from app.services.tts_engine import TTSService


def test_catalogue_covers_exactly_the_engine_preset_speakers():
    """Guards against drift: the catalogue and the TTS engine must agree on
    which speakers exist, or a picker entry synthesizes to an Aiden fallback."""
    assert {p.speaker for p in PRESETS} == set(TTSService.PRESET_SPEAKERS)


def test_only_aiden_and_ryan_are_english():
    english = {p.speaker for p in PRESETS if p.language == "en"}
    assert english == {"Aiden", "Ryan"}


def test_every_preset_has_a_greeting_and_an_english_gloss():
    for p in PRESETS:
        assert p.greeting.strip(), f"{p.speaker} has no greeting"
        assert p.gloss.strip(), f"{p.speaker} has no gloss"


def test_non_english_presets_greet_in_their_own_language():
    """An English sample from a Chinese speaker is the exact bad impression the
    labelling is meant to prevent."""
    for p in PRESETS:
        if p.language != "en":
            assert p.greeting != get_preset("Aiden").greeting


def test_english_presets_use_the_english_greeting():
    assert get_preset("Aiden").greeting == "Welcome to Aria Appeal."
    assert get_preset("Ryan").greeting == "Welcome to Aria Appeal."


def test_languages_covered():
    assert {p.language for p in PRESETS} == {"en", "zh", "ja", "ko"}


def test_get_preset_is_case_sensitive_and_returns_none_for_unknown():
    assert get_preset("Aiden").speaker == "Aiden"
    assert get_preset("Nobody") is None


def test_english_default_is_a_real_english_preset():
    assert get_preset(ENGLISH_DEFAULT).language == "en"
