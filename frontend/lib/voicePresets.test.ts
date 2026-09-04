import { VOICE_PRESETS, PRESET_GROUPS, isPresetSpeaker, DEFAULT_PRESET } from './voicePresets'

describe('voicePresets', () => {
    it('lists all nine Qwen preset speakers', () => {
        expect(VOICE_PRESETS).toHaveLength(9)
    })

    it('marks only Aiden and Ryan as English', () => {
        const english = VOICE_PRESETS.filter(p => p.language === 'en').map(p => p.speaker)
        expect(english.sort()).toEqual(['Aiden', 'Ryan'])
    })

    it('puts the English group first', () => {
        expect(PRESET_GROUPS[0].language).toBe('en')
        expect(PRESET_GROUPS[0].label).toBe('English')
    })

    it('groups the remaining languages after English', () => {
        expect(PRESET_GROUPS.map(g => g.language)).toEqual(['en', 'zh', 'ja', 'ko'])
    })

    it('every group is non-empty and every speaker appears exactly once', () => {
        const flat = PRESET_GROUPS.flatMap(g => g.presets.map(p => p.speaker))
        expect(flat).toHaveLength(9)
        expect(new Set(flat).size).toBe(9)
        PRESET_GROUPS.forEach(g => expect(g.presets.length).toBeGreaterThan(0))
    })

    it('captions non-English voices with the English gloss', () => {
        VOICE_PRESETS.filter(p => p.language !== 'en').forEach(p => {
            expect(p.gloss).toBe('Welcome to Aria Appeal.')
        })
    })

    it('defaults to an English preset', () => {
        expect(VOICE_PRESETS.find(p => p.speaker === DEFAULT_PRESET)?.language).toBe('en')
    })

    it('recognises preset speakers and rejects cloned-profile UUIDs', () => {
        expect(isPresetSpeaker('Aiden')).toBe(true)
        expect(isPresetSpeaker('Ono_Anna')).toBe(true)
        expect(isPresetSpeaker('11111111-2222-3333-4444-555555555555')).toBe(false)
        expect(isPresetSpeaker('default')).toBe(false)
    })
})
