'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import ScriptEditor from '@/components/studio/ScriptEditor';
import WaveformVisualizer from '@/components/studio/WaveformVisualizer';
import InspectorPanel from '@/components/studio/InspectorPanel';
import { useStudioStore } from '@/store/studioStore';
import { API_URL } from '@/lib/config';
import { apiFetch } from '@/lib/api';
import { useSession } from 'next-auth/react';
import toast from 'react-hot-toast';
import Link from 'next/link';
import { ArrowLeft, Download, Loader2, Keyboard } from 'lucide-react';

export default function StudioPage() {
    const params = useParams();
    const projectId = params.id as string;
    const { fetchProjectData, audioUrl, script, generatingSegments } = useStudioStore();
    const [isGenerating, setIsGenerating] = useState(false);
    const [isLoadingProject, setIsLoadingProject] = useState(true);
    const [isAwaitingAudio, setIsAwaitingAudio] = useState(false);
    const { data: session, status } = useSession();
    const [wasRegenerating, setWasRegenerating] = useState(false);

    useEffect(() => {
        let isSubscribed = true;
        let timeoutId: NodeJS.Timeout;

        const pollData = async () => {
            if (projectId && status === 'authenticated') {
                const token = session?.accessToken;
                if (token && isSubscribed) {
                    await fetchProjectData(projectId, token);
                    setIsLoadingProject(false);

                    const profilesRes = await apiFetch('/voice-profiles', { token });
                    if (profilesRes.ok) {
                        const profiles = await profilesRes.json();
                        useStudioStore.getState().setVoiceProfiles(profiles);
                    }

                    const currentScript = useStudioStore.getState().script;
                    const hasScript = currentScript.length > 0;
                    const segmentsWithAudio = currentScript.filter(s => s.audio_url).length;
                    const needsPolling = hasScript && segmentsWithAudio < currentScript.length;

                    setIsAwaitingAudio(needsPolling);

                    if (needsPolling && isSubscribed) {
                        timeoutId = setTimeout(pollData, 5000);
                    } else if (hasScript && !needsPolling && isSubscribed && !useStudioStore.getState().audioUrl && !isGenerating) {
                        handleGenerateFullAudio();
                    }
                }
            }
        };

        pollData();

        return () => {
            isSubscribed = false;
            if (timeoutId) clearTimeout(timeoutId);
        };
    }, [projectId, fetchProjectData, status, session]);

    // Keyboard shortcuts
    const [showShortcuts, setShowShortcuts] = useState(false);

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            const target = e.target as HTMLElement;
            const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;

            // Ctrl+S / Cmd+S — force save (works even in input fields)
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                toast.success('All changes saved');
                return;
            }

            // Don't capture shortcuts when typing in input fields
            if (isInput) return;

            const state = useStudioStore.getState();

            switch (e.key) {
                case ' ':
                    e.preventDefault();
                    state.setIsPlaying(!state.isPlaying);
                    break;
                case 'ArrowRight': {
                    e.preventDefault();
                    const currentIdx = state.script.findIndex(s => s.id === state.activeSegmentId);
                    const nextIdx = currentIdx < state.script.length - 1 ? currentIdx + 1 : 0;
                    state.setActiveSegment(state.script[nextIdx]?.id ?? null);
                    break;
                }
                case 'ArrowLeft': {
                    e.preventDefault();
                    const currentIdx = state.script.findIndex(s => s.id === state.activeSegmentId);
                    const prevIdx = currentIdx > 0 ? currentIdx - 1 : state.script.length - 1;
                    state.setActiveSegment(state.script[prevIdx]?.id ?? null);
                    break;
                }
                case 'Escape':
                    state.setActiveSegment(null);
                    break;
                case '?':
                    setShowShortcuts(prev => !prev);
                    break;
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    // Auto re-export after all segments finish regenerating
    const anyRegenerating = Object.values(generatingSegments).some(Boolean);
    useEffect(() => {
        if (anyRegenerating) {
            setWasRegenerating(true);
        } else if (wasRegenerating && !anyRegenerating) {
            setWasRegenerating(false);
            // All segments done — re-fetch project data to get updated timestamps, then re-export
            const token = session?.accessToken;
            if (token && projectId) {
                fetchProjectData(projectId, token).then(() => {
                    handleGenerateFullAudio();
                });
            }
        }
    }, [anyRegenerating]);

    const handleGenerateFullAudio = async () => {
        setIsGenerating(true);
        try {
            const res = await apiFetch(`/projects/${projectId}/export`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                token: session?.accessToken,
            });
            if (!res.ok) {
                const errorData = await res.json();
                throw new Error(errorData.detail || "Failed to export project");
            }
            const data = await res.json();

            useStudioStore.getState().setAudioUrl(data.master_audio_url);
            toast.success("Project exported successfully!");
        } catch (error: any) {
            console.error("Export error:", error);
            toast.error(error.message);
        } finally {
            setIsGenerating(false);
        }
    };

    const handleDownload = async () => {
        const currentUrl = useStudioStore.getState().audioUrl;
        if (!currentUrl) {
            // Export first, then download
            await handleGenerateFullAudio();
        }
        const url = useStudioStore.getState().audioUrl;
        if (!url) return;

        const baseUrl = API_URL.replace(/\/api\/v1$/, '');
        const fullUrl = url.startsWith('http') ? url : `${baseUrl}${url}`;

        try {
            const res = await fetch(fullUrl);
            const blob = await res.blob();
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `campaign_${projectId}.wav`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(a.href);
            toast.success("Download started!");
        } catch {
            toast.error("Download failed");
        }
    };

    return (
        <div className="flex h-screen w-full bg-moore-cream overflow-hidden flex-col">
            {/* Header */}
            <div className="h-14 border-b border-gray-200 bg-white flex items-center px-5 justify-between shadow-sm">
                <div className="flex items-center gap-4">
                    <Link
                        href="/dashboard"
                        className="flex items-center gap-1.5 text-sm text-moore-mid-gray hover:text-moore-black transition-colors"
                    >
                        <ArrowLeft className="h-4 w-4" />
                        Dashboard
                    </Link>
                    <div className="h-5 w-px bg-gray-200" />
                    <h1 className="font-semibold text-moore-black text-sm">
                        <span className="text-moore-red">M</span>OORE Studio
                    </h1>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => setShowShortcuts(prev => !prev)}
                        className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm text-moore-mid-gray border border-gray-200 hover:bg-gray-50 transition-colors"
                        title="Keyboard shortcuts (?)"
                    >
                        <Keyboard className="h-4 w-4" />
                    </button>
                    {audioUrl && (
                        <button
                            onClick={handleDownload}
                            className="flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium bg-green-50 text-green-700 border border-green-200 hover:bg-green-100 transition-all"
                        >
                            <Download className="h-4 w-4" />
                            Download WAV
                        </button>
                    )}
                    <button
                        onClick={audioUrl ? handleDownload : handleGenerateFullAudio}
                        disabled={isGenerating}
                        className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition-all ${
                            audioUrl
                                ? 'bg-white text-moore-mid-gray border border-gray-200 hover:bg-gray-50'
                                : 'bg-moore-red text-white hover:bg-moore-red-dark shadow-sm'
                        } disabled:opacity-50`}
                    >
                        {isGenerating ? (
                            <><Loader2 className="h-4 w-4 animate-spin" /> Exporting...</>
                        ) : audioUrl ? (
                            'Re-export'
                        ) : (
                            <><Download className="h-4 w-4" /> Export & Download</>
                        )}
                    </button>
                </div>
            </div>

            {isLoadingProject ? (
                <div className="flex-1 flex items-center justify-center">
                    <div className="flex flex-col items-center gap-3">
                        <Loader2 className="h-8 w-8 animate-spin text-moore-red" />
                        <p className="text-sm text-moore-mid-gray">Loading project...</p>
                    </div>
                </div>
            ) : (
                <>
                {isAwaitingAudio && (
                    <div className="flex items-center gap-2 px-5 py-2 bg-moore-red/5 border-b border-moore-red/10">
                        <Loader2 className="h-3.5 w-3.5 animate-spin text-moore-red" />
                        <p className="text-xs text-moore-red font-medium">
                            Generating audio — {script.filter(s => s.audio_url).length}/{script.length} segments ready
                        </p>
                    </div>
                )}
                <div className="flex flex-1 overflow-hidden">
                    {/* Left Column: Script - 30% */}
                    <div className="w-[30%] h-full flex flex-col border-r border-gray-200">
                        <ScriptEditor />
                    </div>

                    {/* Center Column: Waveform - 45% */}
                    <div className="w-[45%] h-full flex flex-col relative bg-white">
                        <div className="flex-1 p-6 flex items-center justify-center">
                            <WaveformVisualizer />
                        </div>
                    </div>

                    {/* Right Column: Inspector - 25% */}
                    <div className="w-[25%] h-full border-l border-gray-200 bg-white">
                        <InspectorPanel />
                    </div>
                </div>
                </>
            )}

            {/* Keyboard Shortcuts Overlay */}
            {showShortcuts && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setShowShortcuts(false)}>
                    <div className="bg-white rounded-2xl p-6 shadow-xl max-w-sm w-full mx-4" onClick={(e) => e.stopPropagation()}>
                        <h3 className="text-sm font-semibold text-moore-dark-gray uppercase tracking-wider mb-4">Keyboard Shortcuts</h3>
                        <div className="space-y-2.5 text-sm">
                            {[
                                ['Space', 'Play / Pause'],
                                ['\u2190', 'Previous segment'],
                                ['\u2192', 'Next segment'],
                                ['Escape', 'Deselect segment'],
                                ['Ctrl+S', 'Save'],
                                ['?', 'Toggle this help'],
                            ].map(([key, desc]) => (
                                <div key={key} className="flex items-center justify-between">
                                    <span className="text-moore-dark-gray">{desc}</span>
                                    <kbd className="px-2 py-1 rounded-lg bg-gray-100 border border-gray-200 text-xs font-mono text-moore-mid-gray">{key}</kbd>
                                </div>
                            ))}
                        </div>
                        <button
                            onClick={() => setShowShortcuts(false)}
                            className="mt-5 w-full rounded-xl bg-gray-100 py-2 text-sm font-medium text-moore-dark-gray hover:bg-gray-200 transition-colors"
                        >
                            Close
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
