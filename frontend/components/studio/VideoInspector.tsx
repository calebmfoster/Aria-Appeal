'use client';

import React, { useState } from 'react';
import { useParams } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import toast from 'react-hot-toast';
import { useStudioStore } from '@/store/studioStore';
import { apiFetch } from '@/lib/api';
import { DEFAULT_SUBTITLE_STYLE } from '@/types/video';
import type { SubtitleStyle } from '@/types/video';

function formatMs(ms?: number | null): string {
    if (ms === null || ms === undefined) return '—';
    return `${(ms / 1000).toFixed(1)}s`;
}

const SOURCE_LABEL: Record<string, string> = {
    generated: 'Generated',
    asset: 'Pre-made asset',
    uploaded: 'Uploaded',
};

const VideoInspector: React.FC = () => {
    const { videoClips, activeClipId, activeSegmentId, script, videoBrief, subtitleStyle, setSubtitleStyle } =
        useStudioStore();
    const { data: session } = useSession();
    const params = useParams();
    const projectId = params?.id as string;
    const [showBible, setShowBible] = useState(false);

    const clip =
        videoClips.find(c => c.id === activeClipId) ??
        videoClips.find(c => c.segment_id === activeSegmentId);
    const segment = script.find(s => s.id === clip?.segment_id);
    const style = subtitleStyle ?? DEFAULT_SUBTITLE_STYLE;

    const persistStyle = async (next: SubtitleStyle) => {
        setSubtitleStyle(next);
        const token = session?.accessToken;
        if (!token || !projectId) return;
        try {
            const res = await apiFetch(`/projects/${projectId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                token,
                body: JSON.stringify({ subtitle_style: next }),
            });
            if (!res.ok) throw new Error('save failed');
        } catch {
            toast.error('Could not save subtitle settings');
        }
    };

    return (
        <div className="h-full p-5 bg-white flex flex-col gap-5 overflow-y-auto">
            <h3 className="text-sm font-semibold text-moore-dark-gray uppercase tracking-wider">
                Clip Inspector
            </h3>

            {!clip ? (
                <p className="text-sm text-moore-mid-gray">
                    Select a shot on the left to see its detail.
                </p>
            ) : (
                <div className="space-y-4">
                    <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 text-[10px] font-semibold uppercase bg-moore-red/10 text-moore-red border border-moore-red/20 rounded-md">
                            {SOURCE_LABEL[clip.source_type] ?? clip.source_type}
                        </span>
                        <span className="text-[11px] text-moore-mid-gray capitalize">{clip.status}</span>
                    </div>

                    <div className="flex gap-3">
                        <div className="flex-1 bg-moore-cream/50 rounded-xl px-3 py-2 border border-gray-100">
                            <p className="text-[10px] text-moore-mid-gray uppercase tracking-wider">Duration</p>
                            <p className="text-sm font-mono text-moore-black">{formatMs(clip.duration_ms)}</p>
                        </div>
                        <div className="flex-1 bg-moore-cream/50 rounded-xl px-3 py-2 border border-gray-100">
                            <p className="text-[10px] text-moore-mid-gray uppercase tracking-wider">Starts at</p>
                            <p className="text-sm font-mono text-moore-black">{formatMs(clip.timeline_start_ms)}</p>
                        </div>
                    </div>

                    {segment && (
                        <div className="space-y-1">
                            <p className="text-[10px] text-moore-mid-gray uppercase tracking-wider">Narration</p>
                            <p className="text-xs leading-relaxed text-moore-dark-gray">{segment.text}</p>
                        </div>
                    )}

                    {clip.prompt && (
                        <div className="space-y-1">
                            <p className="text-[10px] text-moore-mid-gray uppercase tracking-wider">Shot prompt</p>
                            <p className="text-xs leading-relaxed text-moore-mid-gray whitespace-pre-wrap">
                                {clip.prompt}
                            </p>
                        </div>
                    )}
                </div>
            )}

            <div className="border-t border-gray-100 pt-4 space-y-3">
                <div className="flex items-center justify-between">
                    <label className="text-sm font-medium text-moore-dark-gray">Burn in subtitles</label>
                    <input
                        type="checkbox"
                        checked={style.enabled}
                        onChange={e => persistStyle({ ...style, enabled: e.target.checked })}
                        className="h-4 w-4 accent-moore-red"
                    />
                </div>
                <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                        <label className="text-sm font-medium text-moore-dark-gray">Caption size</label>
                        <span className="text-xs text-moore-mid-gray tabular-nums">{style.font_size}</span>
                    </div>
                    <input
                        type="range"
                        min={24} max={80} step={2}
                        value={style.font_size}
                        disabled={!style.enabled}
                        onChange={e => persistStyle({ ...style, font_size: parseInt(e.target.value, 10) })}
                        className="w-full accent-moore-red disabled:opacity-40"
                    />
                </div>
                <p className="text-[10px] text-moore-mid-gray italic">
                    Applies on next assembly — the current video is unchanged.
                </p>
            </div>

            <div className="border-t border-gray-100 pt-4">
                <button
                    onClick={() => setShowBible(v => !v)}
                    className="flex items-center gap-1.5 text-sm font-medium text-moore-dark-gray hover:text-moore-black transition-colors"
                >
                    {showBible ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                    Visual bible
                </button>
                {showBible && (
                    <div className="mt-3 space-y-3">
                        <div className="space-y-1">
                            <p className="text-[10px] text-moore-mid-gray uppercase tracking-wider">Style</p>
                            <p className="text-xs leading-relaxed text-moore-mid-gray whitespace-pre-wrap">
                                {videoBrief?.style_prompt || 'Not set.'}
                            </p>
                        </div>
                        <div className="space-y-1">
                            <p className="text-[10px] text-moore-mid-gray uppercase tracking-wider">Characters</p>
                            <p className="text-xs leading-relaxed text-moore-mid-gray whitespace-pre-wrap">
                                {videoBrief?.character_sheet || 'Not set.'}
                            </p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default VideoInspector;
