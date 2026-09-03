/**
 * Display mirror of backend/app/services/voice_presets.py.
 *
 * Only Aiden and Ryan are native-English Qwen3-TTS presets; the other seven are
 * Chinese, Japanese or Korean. We label rather than hide, and preview each voice
 * in its own language — an English sample from a Chinese speaker is exactly the
 * bad impression the labelling prevents.
 *
 * Scope: this makes the VOICE layer multi-language. Script generation, the studio
 * UI and subtitles remain English-only.
 */

export type PresetLanguage = 'en' | 'zh' | 'ja' | 'ko';

export interface VoicePreset {
    speaker: string;
    label: string;
    language: PresetLanguage;
    languageLabel: string;
    gender: 'male' | 'female';
    accent?: string;
    gloss: string;
}

const GLOSS = 'Welcome to Aria Appeal.';

export const DEFAULT_PRESET = 'Aiden';

export const VOICE_PRESETS: VoicePreset[] = [
    { speaker: 'Aiden', label: 'Aiden — Male', language: 'en', languageLabel: 'English', gender: 'male', gloss: GLOSS },
    { speaker: 'Ryan', label: 'Ryan — Male', language: 'en', languageLabel: 'English', gender: 'male', gloss: GLOSS },
    { speaker: 'Vivian', label: 'Vivian — Female', language: 'zh', languageLabel: 'Chinese', gender: 'female', gloss: GLOSS },
    { speaker: 'Serena', label: 'Serena — Female', language: 'zh', languageLabel: 'Chinese', gender: 'female', gloss: GLOSS },
    { speaker: 'Uncle_Fu', label: 'Uncle Fu — Male', language: 'zh', languageLabel: 'Chinese', gender: 'male', gloss: GLOSS },
    { speaker: 'Dylan', label: 'Dylan — Male, Beijing', language: 'zh', languageLabel: 'Chinese', gender: 'male', accent: 'Beijing', gloss: GLOSS },
    { speaker: 'Eric', label: 'Eric — Male, Sichuan', language: 'zh', languageLabel: 'Chinese', gender: 'male', accent: 'Sichuan', gloss: GLOSS },
    { speaker: 'Ono_Anna', label: 'Ono Anna — Female', language: 'ja', languageLabel: 'Japanese', gender: 'female', gloss: GLOSS },
    { speaker: 'Sohee', label: 'Sohee — Female', language: 'ko', languageLabel: 'Korean', gender: 'female', gloss: GLOSS },
];

// English first — it is the only language the rest of the product speaks.
const LANGUAGE_ORDER: PresetLanguage[] = ['en', 'zh', 'ja', 'ko'];

export interface PresetGroup {
    language: PresetLanguage;
    label: string;
    presets: VoicePreset[];
}

export const PRESET_GROUPS: PresetGroup[] = LANGUAGE_ORDER.map(language => ({
    language,
    label: VOICE_PRESETS.find(p => p.language === language)!.languageLabel,
    presets: VOICE_PRESETS.filter(p => p.language === language),
}));

const SPEAKERS = new Set(VOICE_PRESETS.map(p => p.speaker));

export function isPresetSpeaker(value: string): boolean {
    return SPEAKERS.has(value);
}

export function getPreset(speaker: string): VoicePreset | undefined {
    return VOICE_PRESETS.find(p => p.speaker === speaker);
}
