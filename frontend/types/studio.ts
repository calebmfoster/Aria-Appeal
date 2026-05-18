export interface ScriptSegment {
    id: string; // UUID from backend
    text: string;
    start_ms: number;
    end_ms: number;
    audio_url?: string; // If per-segment audio is tracked
    voice_profile_id?: string;
    speaker_preset?: string;
    emotion?: string;
    pitch_shift?: number;
}

export interface VoiceProfile {
    id: string;
    name: string;
    base_model?: string;
    description?: string;
    preview_url?: string;
    has_cloned_voice?: boolean;
}

export interface AudioRegion {
    id: string;
    start: number; // seconds (wavesurfer uses seconds)
    end: number;   // seconds
    color?: string;
    drag?: boolean;
    resize?: boolean;
}
