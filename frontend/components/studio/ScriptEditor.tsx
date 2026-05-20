'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useStudioStore } from '@/store/studioStore';
import { CheckCircle2, Circle, Loader2, Mic, Trash2, Plus } from 'lucide-react';
import { useSession } from 'next-auth/react';
import { useParams } from 'next/navigation';
import { apiFetch } from '@/lib/api';
import { ScriptSegment } from '@/types/studio';
import toast from 'react-hot-toast';

function formatTime(ms: number): string {
    const totalSec = Math.floor(ms / 1000);
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    const frac = Math.floor((ms % 1000) / 100);
    return `${min}:${sec.toString().padStart(2, '0')}.${frac}`;
}

const ScriptEditor: React.FC = () => {
    const {
        script,
        activeSegmentId,
        setActiveSegment,
        currentTime,
        isPlaying,
        generatingSegments,
        setCurrentTime,
        voiceProfiles,
        dirtySegments,
        updateSegment,
        setSaveStatus,
        markSegmentClean,
        addSegment,
        removeSegment,
        setAudioUrl,
    } = useStudioStore();
    const { data: session } = useSession();
    const params = useParams();
    const projectId = params.id as string;

    const segmentRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});
    const saveTimerRef = useRef<NodeJS.Timeout | null>(null);
    const confirmDeleteTimerRef = useRef<NodeJS.Timeout | null>(null);

    const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
    const [isAddingSegment, setIsAddingSegment] = useState(false);

    useEffect(() => {
        if (activeSegmentId && segmentRefs.current[activeSegmentId]) {
            segmentRefs.current[activeSegmentId]?.scrollIntoView({
                behavior: 'smooth',
                block: 'center',
            });
        }
    }, [activeSegmentId]);

    useEffect(() => {
        return () => {
            if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
            if (confirmDeleteTimerRef.current) clearTimeout(confirmDeleteTimerRef.current);
        };
    }, []);

    const scheduleSave = useCallback((segmentId: string) => {
        if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
        saveTimerRef.current = setTimeout(async () => {
            const state = useStudioStore.getState();
            const segment = state.script.find(s => s.id === segmentId);
            if (!segment || !state.dirtySegments[segmentId]) return;
            const token = session?.accessToken;
            if (!token || !projectId) return;

            setSaveStatus('saving');
            try {
                const body: Record<string, any> = { text: segment.text };
                if (segment.emotion !== undefined) body.emotion = segment.emotion || '';
                if (segment.voice_profile_id !== undefined) body.voice_profile_id = segment.voice_profile_id || null;
                if (segment.speaker_preset !== undefined) body.speaker_preset = segment.speaker_preset || null;
                if (segment.pitch_shift !== undefined) body.pitch_shift = segment.pitch_shift ?? 0;

                const res = await apiFetch(`/projects/${projectId}/segments/${segmentId}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    token,
                    body: JSON.stringify(body),
                });
                if (!res.ok) throw new Error('Save failed');
                markSegmentClean(segmentId);
                setSaveStatus('saved');
                setTimeout(() => {
                    if (useStudioStore.getState().saveStatus === 'saved') setSaveStatus('idle');
                }, 2000);
            } catch {
                setSaveStatus('error');
            }
        }, 800);
    }, [session, projectId, setSaveStatus, markSegmentClean]);

    const handleSegmentClick = (segmentId: string) => {
        if (activeSegmentId === segmentId) return;
        const segment = script.find(s => s.id === segmentId);
        if (!segment) return;
        setActiveSegment(segmentId);
        setCurrentTime(segment.start_ms / 1000);
    };

    const handleTextChange = (segmentId: string, text: string) => {
        updateSegment(segmentId, { text });
        scheduleSave(segmentId);
    };

    const reExportOrClear = async () => {
        const state = useStudioStore.getState();
        const allHaveAudio = state.script.length > 0 && state.script.every(s => s.audio_url);
        if (!allHaveAudio) {
            setAudioUrl(null);
            return;
        }
        const token = session?.accessToken;
        if (!token || !projectId) return;
        try {
            const res = await apiFetch(`/projects/${projectId}/export`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                token,
            });
            if (!res.ok) throw new Error();
            const data = await res.json();
            setAudioUrl(data.master_audio_url);
            toast.success('Waveform updated');
        } catch {
            setAudioUrl(null);
        }
    };

    const handleDeleteClick = (e: React.MouseEvent, segmentId: string) => {
        e.stopPropagation();
        if (confirmDeleteId === segmentId) {
            handleDeleteConfirm(segmentId);
        } else {
            setConfirmDeleteId(segmentId);
            if (confirmDeleteTimerRef.current) clearTimeout(confirmDeleteTimerRef.current);
            confirmDeleteTimerRef.current = setTimeout(() => setConfirmDeleteId(null), 3000);
        }
    };

    const handleDeleteConfirm = async (segmentId: string) => {
        if (confirmDeleteTimerRef.current) clearTimeout(confirmDeleteTimerRef.current);
        setConfirmDeleteId(null);
        const token = session?.accessToken;
        if (!token || !projectId) return;
        try {
            const res = await apiFetch(`/projects/${projectId}/segments/${segmentId}`, {
                method: 'DELETE',
                token,
            });
            if (!res.ok) throw new Error('Delete failed');
            removeSegment(segmentId);
            toast.success('Segment deleted');
            await reExportOrClear();
        } catch {
            toast.error('Failed to delete segment');
        }
    };

    const handleAddSegment = async () => {
        const token = session?.accessToken;
        if (!token || !projectId) return;
        setIsAddingSegment(true);
        try {
            const res = await apiFetch(`/projects/${projectId}/segments`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                token,
                body: JSON.stringify({ text: 'New segment', sequence_order: script.length }),
            });
            if (!res.ok) throw new Error('Add failed');
            const data = await res.json();
            const newSegment: ScriptSegment = {
                id: data.id,
                text: data.text,
                start_ms: data.start_time_ms ?? 0,
                end_ms: data.end_time_ms ?? 0,
                audio_url: data.audio_url ?? undefined,
                emotion: data.emotion ?? undefined,
                voice_profile_id: data.voice_profile_id ?? undefined,
                speaker_preset: data.speaker_preset ?? undefined,
                pitch_shift: data.pitch_shift ?? 0,
            };
            addSegment(newSegment);
            setActiveSegment(newSegment.id);
            setAudioUrl(null); // master is stale until new segment has audio
        } catch {
            toast.error('Failed to add segment');
        } finally {
            setIsAddingSegment(false);
        }
    };

    return (
        <div className="h-full overflow-y-auto p-4 space-y-2 bg-moore-cream/50" onClick={() => setActiveSegment(null)}>
            <h2 className="text-sm font-semibold mb-3 text-moore-dark-gray uppercase tracking-wider">Script</h2>
            {script.length === 0 ? (
                <div className="text-moore-mid-gray text-center text-sm mt-10">No script generated yet.</div>
            ) : (
                script.map((segment) => {
                    const isActive = activeSegmentId === segment.id;
                    const isPlayingCurrent = isPlaying && currentTime >= segment.start_ms / 1000 && currentTime < segment.end_ms / 1000;
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
                            onClick={(e) => { e.stopPropagation(); handleSegmentClick(segment.id); }}
                            className={`p-3 rounded-xl transition-all duration-200 border ${
                                isActive
                                    ? 'bg-white border-moore-red/30 shadow-sm ring-1 ring-moore-red/20 cursor-text'
                                    : isPlayingCurrent
                                        ? 'bg-moore-red/5 border-moore-red/10 cursor-pointer'
                                        : 'bg-white/60 border-transparent hover:bg-white hover:border-gray-200 cursor-pointer'
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
                                    <div className="flex items-start gap-2">
                                        {isActive && !isGenerating ? (
                                            <textarea
                                                autoFocus
                                                value={segment.text}
                                                onChange={e => handleTextChange(segment.id, e.target.value)}
                                                onClick={e => e.stopPropagation()}
                                                rows={Math.max(2, segment.text.split('\n').length)}
                                                className="flex-1 text-sm leading-relaxed text-moore-black font-medium bg-transparent border-0 border-b border-moore-red/30 focus:outline-none focus:border-moore-red resize-none p-0 pb-0.5 min-w-0"
                                            />
                                        ) : (
                                            <p className={`flex-1 text-sm leading-relaxed ${
                                                isPlayingCurrent ? 'text-moore-black font-medium' : 'text-moore-dark-gray'
                                            }`}>
                                                {segment.text}
                                            </p>
                                        )}
                                        {isActive && !isGenerating && (
                                            <button
                                                onClick={(e) => handleDeleteClick(e, segment.id)}
                                                className={`flex-shrink-0 flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded transition-colors mt-0.5 ${
                                                    confirmDeleteId === segment.id
                                                        ? 'text-white bg-red-500 hover:bg-red-600'
                                                        : 'text-moore-mid-gray hover:text-red-500'
                                                }`}
                                            >
                                                <Trash2 className="w-3 h-3" />
                                                {confirmDeleteId === segment.id ? 'Confirm?' : ''}
                                            </button>
                                        )}
                                    </div>
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

            <button
                onClick={(e) => { e.stopPropagation(); handleAddSegment(); }}
                disabled={isAddingSegment}
                className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-dashed border-gray-300 py-2 text-xs text-moore-mid-gray hover:border-moore-red/40 hover:text-moore-red transition-colors disabled:opacity-50"
            >
                {isAddingSegment ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                Add segment
            </button>
        </div>
    );
};

export default ScriptEditor;
