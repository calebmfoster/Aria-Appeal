'use client';

import React, { useEffect, useRef } from 'react';
import { useStudioStore } from '@/store/studioStore';
import { CheckCircle2, Circle, Loader2, Mic } from 'lucide-react';

function formatTime(ms: number): string {
    const totalSec = Math.floor(ms / 1000);
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    const frac = Math.floor((ms % 1000) / 100);
    return `${min}:${sec.toString().padStart(2, '0')}.${frac}`;
}

const ScriptEditor: React.FC = () => {
    const { script, activeSegmentId, setActiveSegment, currentTime, generatingSegments, setCurrentTime, setIsPlaying, voiceProfiles, dirtySegments } = useStudioStore();
    const segmentRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});

    useEffect(() => {
        if (activeSegmentId && segmentRefs.current[activeSegmentId]) {
            segmentRefs.current[activeSegmentId]?.scrollIntoView({
                behavior: 'smooth',
                block: 'center',
            });
        }
    }, [activeSegmentId]);

    const handleSegmentClick = (segmentId: string) => {
        const segment = script.find(s => s.id === segmentId);
        if (!segment) return;

        const isActive = activeSegmentId === segmentId;
        setActiveSegment(isActive ? null : segmentId);

        // Navigate waveform to segment start time
        if (!isActive) {
            setCurrentTime(segment.start_ms / 1000);
        }
    };

    return (
        <div className="h-full overflow-y-auto p-4 space-y-2 bg-moore-cream/50">
            <h2 className="text-sm font-semibold mb-3 text-moore-dark-gray uppercase tracking-wider">Script</h2>
            {script.length === 0 ? (
                <div className="text-moore-mid-gray text-center text-sm mt-10">No script generated yet.</div>
            ) : (
                script.map((segment, index) => {
                    const isActive = activeSegmentId === segment.id;
                    const isPlayingCurrent = currentTime >= segment.start_ms / 1000 && currentTime < segment.end_ms / 1000;
                    const hasAudio = !!segment.audio_url;
                    const isGenerating = generatingSegments[segment.id];
                    const isDirty = dirtySegments[segment.id] || false;
                    const voiceName = segment.voice_profile_id
                        ? voiceProfiles.find(vp => vp.id === segment.voice_profile_id)?.name
                        : null;

                    return (
                        <div
                            key={segment.id}
                            ref={(el) => { segmentRefs.current[segment.id] = el; }}
                            onClick={() => handleSegmentClick(segment.id)}
                            className={`p-3 rounded-xl cursor-pointer transition-all duration-200 border ${
                                isActive
                                    ? 'bg-white border-moore-red/30 shadow-sm ring-1 ring-moore-red/20'
                                    : isPlayingCurrent
                                        ? 'bg-moore-red/5 border-moore-red/10'
                                        : 'bg-white/60 border-transparent hover:bg-white hover:border-gray-200'
                            }`}
                        >
                            <div className="flex items-start gap-2.5">
                                <div className="mt-0.5 flex-shrink-0 relative">
                                    {isGenerating ? (
                                        <Loader2 className="w-4 h-4 text-moore-red animate-spin" />
                                    ) : hasAudio ? (
                                        <CheckCircle2 className={`w-4 h-4 ${isDirty ? 'text-orange-400' : 'text-green-500'}`} />
                                    ) : (
                                        <Circle className="w-4 h-4 text-gray-300" />
                                    )}
                                    {isDirty && !isGenerating && (
                                        <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-orange-400 rounded-full" />
                                    )}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className={`text-sm leading-relaxed ${
                                        isActive ? 'text-moore-black font-medium' : 'text-moore-dark-gray'
                                    }`}>
                                        {segment.text}
                                    </p>
                                    <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                                        {hasAudio && (segment.start_ms > 0 || segment.end_ms > 0) ? (
                                            <span className="text-[10px] font-mono text-moore-mid-gray bg-gray-100 px-1.5 py-0.5 rounded">
                                                {formatTime(segment.start_ms)} – {formatTime(segment.end_ms)}
                                            </span>
                                        ) : !hasAudio ? (
                                            <span className="text-[10px] text-moore-mid-gray bg-gray-50 px-1.5 py-0.5 rounded italic">
                                                Awaiting audio...
                                            </span>
                                        ) : null}
                                        {voiceName && (
                                            <span className="inline-flex items-center gap-0.5 text-[10px] text-moore-red bg-moore-red/5 border border-moore-red/15 px-1.5 py-0.5 rounded">
                                                <Mic className="w-2.5 h-2.5" />
                                                {voiceName}
                                            </span>
                                        )}
                                        {!voiceName && !segment.voice_profile_id && (
                                            <span className="text-[10px] text-moore-mid-gray bg-gray-50 px-1.5 py-0.5 rounded">
                                                Default
                                            </span>
                                        )}
                                        {segment.emotion && (
                                            <span className="text-[10px] text-moore-mid-gray italic">
                                                {segment.emotion}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    );
                })
            )}
        </div>
    );
};

export default ScriptEditor;
