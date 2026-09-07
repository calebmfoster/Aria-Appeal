'use client';

import React from 'react';
import { useStudioStore } from '@/store/studioStore';
import { API_URL } from '@/lib/config';
import { Film } from 'lucide-react';
import type { VideoClip, VideoClipStatus } from '@/types/video';

export function mediaUrl(url?: string | null): string {
    if (!url) return '';
    if (url.startsWith('http')) return url;
    return `${API_URL.replace(/\/api\/v1$/, '')}${url}`;
}

const STATUS_DOT: Record<VideoClipStatus, string> = {
    ready: 'bg-green-500',
    generating: 'bg-amber-400 animate-pulse',
    pending: 'bg-gray-300',
    failed: 'bg-red-500',
};

const STATUS_LABEL: Record<VideoClipStatus, string> = {
    ready: 'Clip ready',
    generating: 'Clip generating',
    pending: 'Clip not generated yet',
    failed: 'Clip failed',
};

const VideoSegmentList: React.FC = () => {
    const { script, videoClips, activeSegmentId, setActiveSegment, setActiveClip } = useStudioStore();

    const clipFor = (segmentId: string): VideoClip | undefined =>
        videoClips.find(c => c.segment_id === segmentId);

    const handleClick = (segmentId: string) => {
        setActiveSegment(segmentId);
        setActiveClip(clipFor(segmentId)?.id ?? null);
    };

    return (
        <div className="h-full overflow-y-auto p-4 space-y-2">
            <h3 className="text-sm font-semibold text-moore-dark-gray uppercase tracking-wider mb-3">
                Shots
            </h3>

            {script.length === 0 && (
                <p className="text-sm text-moore-mid-gray italic">No segments yet.</p>
            )}

            {script.map((segment, index) => {
                const clip = clipFor(segment.id);
                const status: VideoClipStatus = clip?.status ?? 'pending';
                const isActive = segment.id === activeSegmentId;

                return (
                    <button
                        key={segment.id}
                        onClick={() => handleClick(segment.id)}
                        className={`w-full text-left p-2.5 rounded-xl border flex gap-3 transition-all ${
                            isActive
                                ? 'bg-white border-moore-red/30 shadow-sm ring-1 ring-moore-red/20'
                                : 'bg-white/60 border-transparent hover:bg-white hover:border-gray-200'
                        }`}
                    >
                        <div className="relative flex-shrink-0 w-20 h-[45px] rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center">
                            {clip?.video_url ? (
                                <video
                                    src={mediaUrl(clip.video_url)}
                                    muted
                                    playsInline
                                    preload="metadata"
                                    aria-hidden="true"
                                    className="w-full h-full object-cover pointer-events-none"
                                />
                            ) : (
                                <Film className="w-4 h-4 text-gray-300" />
                            )}
                            <span
                                title={STATUS_LABEL[status]}
                                className={`absolute top-1 right-1 w-2 h-2 rounded-full ring-1 ring-white ${STATUS_DOT[status]}`}
                            />
                        </div>

                        <div className="flex-1 min-w-0">
                            <p className="text-[10px] font-semibold uppercase tracking-wider text-moore-mid-gray">
                                Scene {index + 1}
                            </p>
                            <p className="text-xs leading-relaxed text-moore-black line-clamp-3">
                                {segment.text}
                            </p>
                        </div>
                    </button>
                );
            })}
        </div>
    );
};

export default VideoSegmentList;
