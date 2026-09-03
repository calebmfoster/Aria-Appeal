export type CampaignMedium = 'audio' | 'video';

export type StudioTab = 'audio' | 'video';

export type VideoClipStatus = 'pending' | 'generating' | 'ready' | 'failed';

export type VideoSourceType = 'generated' | 'asset' | 'uploaded';

export interface VideoClip {
    id: string;
    project_id: string;
    segment_id?: string | null;
    sequence_order: number;
    source_type: VideoSourceType;
    status: VideoClipStatus;
    prompt?: string | null;
    video_url?: string | null;
    duration_ms?: number | null;
    trim_start_ms?: number | null;
    trim_end_ms?: number | null;
    timeline_start_ms?: number | null;
    timeline_end_ms?: number | null;
}

export interface VideoBrief {
    style_prompt?: string | null;
    character_sheet?: string | null;
    video_master_url?: string | null;
}

export interface SubtitleStyle {
    enabled: boolean;
    font_size: number;
    position: 'bottom' | 'top' | 'center';
    color: string;
}

export const DEFAULT_SUBTITLE_STYLE: SubtitleStyle = {
    enabled: true,
    font_size: 54,
    position: 'bottom',
    color: 'FFFFFF',
};

export type VideoExportStatus = 'idle' | 'running' | 'ready' | 'failed';

export interface VideoExportState {
    status: VideoExportStatus;
    url: string | null;
    error: string | null;
}

export const IDLE_EXPORT: VideoExportState = { status: 'idle', url: null, error: null };
