"""The nine Qwen3-TTS CustomVoice preset speakers, with the language each is
native to.

Per the Qwen3-TTS-12Hz-1.7B-CustomVoice model card only Aiden and Ryan are
English; the rest are Chinese, Japanese or Korean and read English badly. Qwen's
own guidance is to use each speaker's native language, so previews greet in the
speaker's language and carry an English gloss for the caption.

This is the source of truth for synthesis. frontend/lib/voicePresets.ts mirrors
the display fields; test_voice_presets.py guards both against drift with the
engine's PRESET_SPEAKERS list.
"""
from dataclasses import dataclass
from typing import Optional

ENGLISH_DEFAULT = "Aiden"

_GREETINGS = {
    "en": "Welcome to Aria Appeal.",
    "zh": "欢迎使用 Aria Appeal。",
    "ja": "Aria Appeal へようこそ。",
    "ko": "Aria Appeal에 오신 것을 환영합니다.",
}

_ENGLISH_GLOSS = "Welcome to Aria Appeal."


@dataclass(frozen=True)
class VoicePreset:
    speaker: str
    language: str          # ISO-639-1: en / zh / ja / ko
    language_label: str    # human label for the picker group heading
    gender: str            # "female" | "male"
    accent: Optional[str] = None  # regional note, e.g. "Beijing"

    @property
    def greeting(self) -> str:
        """The preview line, in this speaker's own language."""
        return _GREETINGS[self.language]

    @property
    def gloss(self) -> str:
        """English caption shown next to a non-English preview."""
        return _ENGLISH_GLOSS

    @property
    def label(self) -> str:
        gender = self.gender.capitalize()
        base = f"{self.speaker.replace('_', ' ')} — {gender}"
        return f"{base} ({self.language_label}, {self.accent})" if self.accent \
            else f"{base} ({self.language_label})"


PRESETS = (
    VoicePreset("Aiden", "en", "English", "male"),
    VoicePreset("Ryan", "en", "English", "male"),
    VoicePreset("Vivian", "zh", "Chinese", "female"),
    VoicePreset("Serena", "zh", "Chinese", "female"),
    VoicePreset("Uncle_Fu", "zh", "Chinese", "male"),
    VoicePreset("Dylan", "zh", "Chinese", "male", accent="Beijing"),
    VoicePreset("Eric", "zh", "Chinese", "male", accent="Sichuan"),
    VoicePreset("Ono_Anna", "ja", "Japanese", "female"),
    VoicePreset("Sohee", "ko", "Korean", "female"),
)

_BY_SPEAKER = {p.speaker: p for p in PRESETS}


def get_preset(speaker: str) -> Optional[VoicePreset]:
    return _BY_SPEAKER.get(speaker)
