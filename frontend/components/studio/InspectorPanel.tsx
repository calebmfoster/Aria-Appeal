'use client';

import React, { useEffect, useRef, useCallback, useState } from 'react';
import { useStudioStore } from '@/store/studioStore';
import { Textarea } from '@/components/ui/textarea';
import { useSession } from 'next-auth/react';
import { API_URL } from '@/lib/config';
import toast from 'react-hot-toast';
import { Loader2, Check, AlertCircle, Wand2 } from 'lucide-react';
import { useParams } from 'next/navigation';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

function formatTime(ms: number): string {
    const totalSec = Math.floor(ms / 1000);
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    const frac = Math.floor((ms % 1000) / 100);
    return `${min}:${sec.toString().padStart(2, '0')}.${frac}`;
}

const InspectorPanel: React.FC = () => {
    const {
        activeSegmentId,
        script,
        updateSegment,
        setAudioUrl,
        generatingSegments,
        setGeneratingSegment,
        voiceProfiles,
        saveStatus,
        setSaveStatus,
        dirtySegments,
        markSegmentClean,
    } = useStudioStore();
    const { data: session } = useSession();
    const params = useParams();
    const projectId = params.id as string;
    const saveTimerRef = useRef<NodeJS.Timeout | null>(null);

    const activeSegment = script.find(s => s.id === activeSegmentId);
    const [rewritePrompt, setRewritePrompt] = useState('');
    const [isRewriting, setIsRewriting] = useState(false);

    // Debounced auto-save: saves dirty segment to backend after 800ms of inactivity
    const scheduleSave = useCallback((segmentId: string) => {
        if (saveTimerRef.current) clearTimeout(saveTimerRef.current);

        saveTimerRef.current = setTimeout(async () => {
            const state = useStudioStore.getState();
            const segment = state.script.find(s => s.id === segmentId);
            if (!segment || !state.dirtySegments[segmentId]) return;

            const token = (session as any)?.accessToken;
            if (!token || !projectId) return;

            setSaveStatus('saving');
            try {
                const body: Record<string, any> = { text: segment.text };
                if (segment.emotion !== undefined) body.emotion = segment.emotion || '';
                if (segment.voice_profile_id !== undefined) body.voice_profile_id = segment.voice_profile_id || null;
                if (segment.speaker_preset !== undefined) body.speaker_preset = segment.speaker_preset || null;
                if (segment.pitch_shift !== undefined) body.pitch_shift = segment.pitch_shift ?? 0;

                const res = await fetch(`${API_URL}/projects/${projectId}/segments/${segmentId}`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`,
                    },
                    body: JSON.stringify(body),
                });

                if (!res.ok) throw new Error('Save failed');
                markSegmentClean(segmentId);
                setSaveStatus('saved');
                // Reset to idle after 2s
                setTimeout(() => {
                    if (useStudioStore.getState().saveStatus === 'saved') {
                        setSaveStatus('idle');
                    }
                }, 2000);
            } catch {
                setSaveStatus('error');
            }
        }, 800);
    }, [session, projectId, setSaveStatus, markSegmentClean]);

    // Clean up timer on unmount
    useEffect(() => {
        return () => {
            if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
        };
    }, []);

    const handleTextChange = (text: string) => {
        if (!activeSegment) return;
        updateSegment(activeSegment.id, { text });
        scheduleSave(activeSegment.id);
    };

    const PRESET_SPEAKERS = [
        { value: 'Aiden',    label: 'Aiden — Male (default)' },
        { value: 'Serena',   label: 'Serena — Female' },
        { value: 'Vivian',   label: 'Vivian — Female' },
        { value: 'Ryan',     label: 'Ryan — Male' },
        { value: 'Dylan',    label: 'Dylan — Male' },
        { value: 'Sohee',    label: 'Sohee — Female' },
    ];

    const handleVoiceChange = (val: string) => {
        if (!activeSegment) return;
        const isPreset = PRESET_SPEAKERS.some(p => p.value === val);
        if (val === 'default') {
            updateSegment(activeSegment.id, { voice_profile_id: undefined, speaker_preset: undefined });
        } else if (isPreset) {
            updateSegment(activeSegment.id, { voice_profile_id: undefined, speaker_preset: val });
        } else {
            updateSegment(activeSegment.id, { voice_profile_id: val, speaker_preset: undefined });
        }
        scheduleSave(activeSegment.id);
    };

    const handlePitchChange = (semitones: number) => {
        if (!activeSegment) return;
        updateSegment(activeSegment.id, { pitch_shift: semitones });
        scheduleSave(activeSegment.id);
    };

    const handleEmotionChange = (emotion: string) => {
        if (!activeSegment) return;
        updateSegment(activeSegment.id, { emotion });
        scheduleSave(activeSegment.id);
    };

    const handleRewrite = async () => {
        if (!activeSegment || !rewritePrompt.trim()) return;
        setIsRewriting(true);
        try {
            const token = (session as any)?.accessToken;
            if (!token) throw new Error('Not authenticated');

            const res = await fetch(`${API_URL}/projects/rewrite-segment`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({
                    text: activeSegment.text,
                    prompt: rewritePrompt.trim(),
                }),
            });

            if (!res.ok) throw new Error('Rewrite failed');
            const data = await res.json();
            handleTextChange(data.rewritten_text);
            setRewritePrompt('');
            toast.success('Text rewritten');
        } catch {
            toast.error('Failed to rewrite segment');
        } finally {
            setIsRewriting(false);
        }
    };

    const handleGenerateSegment = async () => {
        if (!activeSegment) return;

        // Read latest state directly from the store to avoid stale closures
        const segmentId = activeSegment.id;
        const latestSegment = useStudioStore.getState().script.find(s => s.id === segmentId);
        if (!latestSegment) return;

        setGeneratingSegment(segmentId, true);
        try {
            const token = (session as any)?.accessToken;
            if (!token) throw new Error("Not authenticated");

            console.log('[Regenerate] Sending text:', latestSegment.text.substring(0, 60), '...');
            console.log('[Regenerate] Emotion:', latestSegment.emotion);
            console.log('[Regenerate] Voice:', latestSegment.voice_profile_id);

            const response = await fetch(`${API_URL}/regenerate-segment`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    sentence_id: latestSegment.id,
                    text: latestSegment.text,
                    start_ms: latestSegment.start_ms,
                    end_ms: latestSegment.end_ms,
                    original_file_url: null,
                    emotion: latestSegment.emotion || '',
                    voice_profile_id: latestSegment.voice_profile_id || null
                })
            });

            if (!response.ok) throw new Error('Generation failed');

            const data = await response.json();
            await pollTask(data.task_id, token, segmentId);

        } catch (error) {
            console.error(error);
            toast.error('Failed to generate audio segment.');
            setGeneratingSegment(segmentId, false);
        }
    };

    const pollTask = async (taskId: string, token: string, segmentId: string) => {
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`${API_URL}/generate-audio/${taskId}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const statusData = await res.json();

                if (statusData.status === 'SUCCESS') {
                    clearInterval(interval);

                    if (statusData.result) {
                        updateSegment(segmentId, { audio_url: statusData.result });
                        markSegmentClean(segmentId);
                        setAudioUrl(null);
                        toast.success('Audio generation complete');
                    } else {
                        toast.error('Task succeeded but no audio URL was returned.');
                    }
                    setGeneratingSegment(segmentId, false);
                } else if (statusData.status === 'FAILURE') {
                    clearInterval(interval);
                    toast.error('Audio generation failed. Check backend logs.');
                    setGeneratingSegment(segmentId, false);
                }
            } catch (error) {
                console.error("Poll Error:", error);
                clearInterval(interval);
                setGeneratingSegment(segmentId, false);
            }
        }, 1500);
    };

    const handleRegenerateAll = async () => {
        const token = (session as any)?.accessToken;
        if (!token) return;

        toast.success("Regenerating all segments...");

        const currentScript = useStudioStore.getState().script;

        currentScript.forEach(async (seg) => {
            setGeneratingSegment(seg.id, true);
            try {
                const response = await fetch(`${API_URL}/regenerate-segment`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        sentence_id: seg.id,
                        text: seg.text,
                        start_ms: seg.start_ms,
                        end_ms: seg.end_ms,
                        original_file_url: null,
                        emotion: seg.emotion || '',
                        voice_profile_id: seg.voice_profile_id || null
                    })
                });

                if (response.ok) {
                    const data = await response.json();
                    pollTask(data.task_id, token, seg.id);
                } else {
                    setGeneratingSegment(seg.id, false);
                }
            } catch (e) {
                setGeneratingSegment(seg.id, false);
            }
        });
    };

    const SaveStatusIndicator = () => {
        if (saveStatus === 'saving') {
            return (
                <span className="flex items-center gap-1 text-[10px] text-moore-mid-gray">
                    <Loader2 className="h-3 w-3 animate-spin" /> Saving...
                </span>
            );
        }
        if (saveStatus === 'saved') {
            return (
                <span className="flex items-center gap-1 text-[10px] text-green-600">
                    <Check className="h-3 w-3" /> Saved
                </span>
            );
        }
        if (saveStatus === 'error') {
            return (
                <span className="flex items-center gap-1 text-[10px] text-red-500">
                    <AlertCircle className="h-3 w-3" /> Save failed
                </span>
            );
        }
        return null;
    };

    // Global Settings (no segment selected)
    if (!activeSegment) {
        return (
            <div className="h-full p-5 bg-white flex flex-col gap-5">
                <h3 className="text-sm font-semibold text-moore-dark-gray uppercase tracking-wider">Global Settings</h3>
                <p className="text-sm text-moore-mid-gray">
                    Select a segment in the script to edit its text, voice, or emotion.
                </p>

                <div className="space-y-4 border-t border-gray-100 pt-5">
                    <div className="space-y-1.5">
                        <label className="text-sm font-medium text-moore-dark-gray">Global Voice Profile</label>
                        <Select
                            value={script.length > 0 && script.every(s => s.voice_profile_id === script[0]?.voice_profile_id) ? (script[0]?.voice_profile_id || "default") : "default"}
                            onValueChange={(val) => {
                                const voiceId = val === "default" ? undefined : val;
                                script.forEach(s => {
                                    updateSegment(s.id, { voice_profile_id: voiceId });
                                    scheduleSave(s.id);
                                });
                                toast.success("Voice profile applied to all segments.");
                            }}
                        >
                            <SelectTrigger className="rounded-xl border-gray-200 focus:ring-moore-red/30">
                                <SelectValue placeholder="Select a voice profile..." />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="default">Default / Auto</SelectItem>
                                {voiceProfiles.map(vp => (
                                    <SelectItem key={vp.id} value={vp.id}>{vp.name}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <button
                        onClick={handleRegenerateAll}
                        disabled={script.some(s => generatingSegments[s.id])}
                        className="flex w-full items-center justify-center gap-2 rounded-xl bg-moore-red px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-moore-red-dark transition-all active:scale-[0.98] disabled:opacity-50"
                    >
                        {script.some(s => generatingSegments[s.id]) ? (
                            <>
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Regenerating {script.filter(s => !generatingSegments[s.id]).length}/{script.length}...
                            </>
                        ) : (
                            'Regenerate All Segments'
                        )}
                    </button>
                </div>
            </div>
        );
    }

    const isDirty = dirtySegments[activeSegment.id] || false;

    // Segment Inspector
    return (
        <div className="h-full p-5 bg-white flex flex-col gap-5 overflow-y-auto">
            <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-moore-dark-gray uppercase tracking-wider">Inspector</h3>
                <SaveStatusIndicator />
            </div>

            {/* Timestamps — only show when audio exists and times are calculated */}
            {activeSegment.audio_url && (activeSegment.start_ms > 0 || activeSegment.end_ms > 0) && (
                <div className="flex gap-3">
                    <div className="flex-1 bg-moore-cream/50 rounded-xl px-3 py-2 border border-gray-100">
                        <p className="text-[10px] text-moore-mid-gray uppercase tracking-wider">Start</p>
                        <p className="text-sm font-mono text-moore-black">{formatTime(activeSegment.start_ms)}</p>
                    </div>
                    <div className="flex-1 bg-moore-cream/50 rounded-xl px-3 py-2 border border-gray-100">
                        <p className="text-[10px] text-moore-mid-gray uppercase tracking-wider">End</p>
                        <p className="text-sm font-mono text-moore-black">{formatTime(activeSegment.end_ms)}</p>
                    </div>
                </div>
            )}

            <div className="space-y-1.5">
                <label className="text-sm font-medium text-moore-dark-gray">Script Text</label>
                <Textarea
                    value={activeSegment.text}
                    onChange={(e) => handleTextChange(e.target.value)}
                    className="rounded-xl border-gray-200 focus:ring-moore-red/30 text-sm"
                />
            </div>

            {/* Prompt-Based Rewrite */}
            <div className="space-y-1.5">
                <label className="text-sm font-medium text-moore-dark-gray flex items-center gap-1.5">
                    <Wand2 className="h-3.5 w-3.5 text-moore-red" />
                    AI Rewrite
                </label>
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={rewritePrompt}
                        onChange={(e) => setRewritePrompt(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleRewrite(); } }}
                        placeholder="e.g. make it more urgent, shorten to 2 sentences"
                        disabled={isRewriting}
                        className="flex-1 rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-moore-red/30 focus:border-moore-red disabled:opacity-50"
                    />
                    <button
                        onClick={handleRewrite}
                        disabled={isRewriting || !rewritePrompt.trim()}
                        className="flex items-center gap-1.5 rounded-xl bg-moore-red/10 px-3 py-2 text-sm font-medium text-moore-red hover:bg-moore-red/20 transition-colors disabled:opacity-50"
                    >
                        {isRewriting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Wand2 className="h-3.5 w-3.5" />}
                    </button>
                </div>
            </div>

            <div className="space-y-1.5">
                <label className="text-sm font-medium text-moore-dark-gray">Voice</label>
                <Select
                    value={activeSegment.speaker_preset || activeSegment.voice_profile_id || "default"}
                    onValueChange={handleVoiceChange}
                >
                    <SelectTrigger className="rounded-xl border-gray-200 focus:ring-moore-red/30">
                        <SelectValue placeholder="Select a voice..." />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="default">Default / Auto</SelectItem>
                        {PRESET_SPEAKERS.map(p => (
                            <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                        ))}
                        {voiceProfiles.length > 0 && (
                            <>
                                <div className="px-2 py-1 text-[10px] font-semibold text-moore-mid-gray uppercase tracking-wider">Cloned Voices</div>
                                {voiceProfiles.map(vp => (
                                    <SelectItem key={vp.id} value={vp.id}>{vp.name}</SelectItem>
                                ))}
                            </>
                        )}
                    </SelectContent>
                </Select>
            </div>

            <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                    <label className="text-sm font-medium text-moore-dark-gray">Pitch</label>
                    <span className="text-xs text-moore-mid-gray tabular-nums">
                        {(activeSegment.pitch_shift ?? 0) > 0 ? '+' : ''}{(activeSegment.pitch_shift ?? 0).toFixed(1)} st
                    </span>
                </div>
                <input
                    type="range"
                    min={-6} max={6} step={0.5}
                    value={activeSegment.pitch_shift ?? 0}
                    onChange={e => handlePitchChange(parseFloat(e.target.value))}
                    className="w-full accent-moore-red"
                />
                <div className="flex justify-between text-[10px] text-moore-mid-gray">
                    <span>−6 st</span><span>0</span><span>+6 st</span>
                </div>
            </div>

            <div className="space-y-1.5">
                <label className="text-sm font-medium text-moore-dark-gray">Emotion / Direction</label>
                <Textarea
                    placeholder={`e.g. "Sadly, slowly at first. Then building with a note of resolve and hope from the 4th sentence onward."`}
                    value={activeSegment.emotion || ''}
                    onChange={(e) => handleEmotionChange(e.target.value)}
                    className="rounded-xl border-gray-200 focus:ring-moore-red/30 text-sm"
                />
                {activeSegment.voice_profile_id && (
                    <p className="text-[10px] text-moore-mid-gray italic">
                        Cloned voices don't support emotion directions — text is synthesized as-is.
                    </p>
                )}
            </div>

            <button
                onClick={handleGenerateSegment}
                disabled={generatingSegments[activeSegment.id]}
                className={`flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all active:scale-[0.98] disabled:opacity-50 ${
                    isDirty
                        ? 'bg-orange-500 hover:bg-orange-600 animate-pulse'
                        : 'bg-moore-red hover:bg-moore-red-dark'
                }`}
            >
                {generatingSegments[activeSegment.id] ? (
                    <><Loader2 className="h-4 w-4 animate-spin" /> Regenerating...</>
                ) : isDirty ? (
                    'Regenerate (text changed)'
                ) : (
                    'Regenerate Segment'
                )}
            </button>
        </div>
    );
};

export default InspectorPanel;
