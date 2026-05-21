import { create } from 'zustand';
import { ScriptSegment, VoiceProfile } from '../types/studio';

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

interface StudioState {
    // Data
    script: ScriptSegment[];
    originalScript: Record<string, { text: string; emotion?: string; voice_profile_id?: string; speaker_preset?: string }>;
    voiceProfiles: VoiceProfile[];

    // Playback State
    audioUrl: string | null;
    isPlaying: boolean;
    currentTime: number;
    duration: number;

    // Selection State
    activeSegmentId: string | null;

    // Generation State
    generatingSegments: Record<string, boolean>;

    // Save State
    saveStatus: SaveStatus;
    dirtySegments: Record<string, boolean>;

    // Actions
    setScript: (script: ScriptSegment[]) => void;
    updateSegment: (id: string, updates: Partial<ScriptSegment>) => void;
    setVoiceProfiles: (profiles: VoiceProfile[]) => void;

    setAudioUrl: (url: string | null) => void;
    setIsPlaying: (isPlaying: boolean) => void;
    setCurrentTime: (time: number) => void;
    setDuration: (duration: number) => void;

    setActiveSegment: (id: string | null) => void;
    setGeneratingSegment: (id: string, isGenerating: boolean) => void;
    fetchProjectData: (projectId: string, token: string) => Promise<void>;
    addSegment: (segment: ScriptSegment) => void;
    removeSegment: (id: string) => void;
    reorderSegments: (orderedIds: string[]) => void;

    // Save actions
    setSaveStatus: (status: SaveStatus) => void;
    markSegmentClean: (id: string) => void;
}

import { API_URL } from '../lib/config';

export const useStudioStore = create<StudioState>((set, get) => ({
    // Initial State
    script: [],
    originalScript: {},
    voiceProfiles: [],
    audioUrl: null,
    isPlaying: false,
    currentTime: 0,
    duration: 0,
    activeSegmentId: null,
    generatingSegments: {},
    saveStatus: 'idle',
    dirtySegments: {},

    // Actions
    setScript: (script) => set({ script }),

    updateSegment: (id, updates) => {
        const state = get();
        const original = state.originalScript[id];
        const segment = state.script.find(s => s.id === id);
        if (!segment) return;

        const updated = { ...segment, ...updates };

        // Determine if this segment is now dirty compared to original
        const isDirty = original ? (
            updated.text !== original.text ||
            (updated.emotion || '') !== (original.emotion || '') ||
            (updated.voice_profile_id || '') !== (original.voice_profile_id || '') ||
            (updated.speaker_preset || '') !== (original.speaker_preset || '')
        ) : false;

        set((state) => ({
            script: state.script.map((seg) =>
                seg.id === id ? { ...seg, ...updates } : seg
            ),
            dirtySegments: { ...state.dirtySegments, [id]: isDirty },
        }));
    },

    setVoiceProfiles: (profiles) => set({ voiceProfiles: profiles }),

    setAudioUrl: (url) => set({ audioUrl: url }),
    setIsPlaying: (isPlaying) => set({ isPlaying }),
    setCurrentTime: (currentTime) => set({ currentTime }),
    setDuration: (duration) => set({ duration }),

    setActiveSegment: (activeSegmentId) => set({ activeSegmentId }),

    setGeneratingSegment: (id, isGenerating) => set((state) => ({
        generatingSegments: {
            ...state.generatingSegments,
            [id]: isGenerating
        }
    })),

    addSegment: (segment) => set((state) => ({
        script: [...state.script, segment],
    })),

    removeSegment: (id) => set((state) => ({
        script: state.script.filter(s => s.id !== id),
        activeSegmentId: state.activeSegmentId === id ? null : state.activeSegmentId,
        dirtySegments: Object.fromEntries(Object.entries(state.dirtySegments).filter(([k]) => k !== id)),
        generatingSegments: Object.fromEntries(Object.entries(state.generatingSegments).filter(([k]) => k !== id)),
    })),

    reorderSegments: (orderedIds) => set((state) => ({
        script: orderedIds
            .map(id => state.script.find(s => s.id === id))
            .filter((s): s is ScriptSegment => s !== undefined),
    })),

    setSaveStatus: (saveStatus) => set({ saveStatus }),

    markSegmentClean: (id) => set((state) => {
        const segment = state.script.find(s => s.id === id);
        if (!segment) return state;
        return {
            dirtySegments: { ...state.dirtySegments, [id]: false },
            originalScript: {
                ...state.originalScript,
                [id]: {
                    text: segment.text,
                    emotion: segment.emotion,
                    voice_profile_id: segment.voice_profile_id,
                    speaker_preset: segment.speaker_preset,
                },
            },
        };
    }),

    fetchProjectData: async (projectId, token) => {
        try {
            const res = await fetch(`${API_URL}/projects/${projectId}`, {
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                }
            });
            if (!res.ok) throw new Error("Failed to fetch project");
            const project = await res.json();

            // Map backend segments to frontend state
            const mappedScript = (project.segments || []).map((seg: any) => ({
                id: seg.id,
                text: seg.text,
                start_ms: seg.start_time_ms || 0,
                end_ms: seg.end_time_ms || 0,
                audio_url: seg.audio_url || undefined,
                emotion: seg.emotion || undefined,
                voice_profile_id: seg.voice_profile_id || undefined,
                speaker_preset: seg.speaker_preset || undefined,
            }));

            // Store original state for dirty tracking
            const originalScript: Record<string, { text: string; emotion?: string; voice_profile_id?: string; speaker_preset?: string }> = {};
            for (const seg of mappedScript) {
                originalScript[seg.id] = {
                    text: seg.text,
                    emotion: seg.emotion,
                    voice_profile_id: seg.voice_profile_id,
                    speaker_preset: seg.speaker_preset,
                };
            }

            set({
                script: mappedScript,
                originalScript,
                dirtySegments: {},
                audioUrl: null,
                activeSegmentId: null,
                isPlaying: false,
                generatingSegments: {},
                saveStatus: 'idle',
            });
        } catch (error) {
            console.error("Error fetching project:", error);
        }
    }
}));
