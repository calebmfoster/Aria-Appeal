'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, Clapperboard, Film, Loader2, RotateCw } from 'lucide-react';
import { useStudioStore } from '@/store/studioStore';
import { mediaUrl } from './VideoSegmentList';
import type { VideoClip, VideoExportState } from '@/types/video';

interface VideoPreviewProps {
    exportState: VideoExportState;
    onAssemble: () => void;
}

function formatSeconds(ms: number): string {
    const total = Math.round(ms / 1000);
    return `${Math.floor(total / 60)}:${(total % 60).toString().padStart(2, '0')}`;
}

/** Timeline positions are written by assembly. Before the first assembly they
 *  are null, so fall back to a running sum of the clips' natural durations. */
function withPositions(clips: VideoClip[]) {
    let cursor = 0;
    return [...clips]
        .sort((a, b) => a.sequence_order - b.sequence_order)
        .map(clip => {
            const start = clip.timeline_start_ms ?? cursor;
            const end = clip.timeline_end_ms ?? start + (clip.duration_ms ?? 0);
            cursor = end;
            return { clip, start, end };
        });
}

const VideoPreview: React.FC<VideoPreviewProps> = ({ exportState, onAssemble }) => {
    const videoRef = useRef<HTMLVideoElement | null>(null);
    const [currentMs, setCurrentMs] = useState(0);
    const { videoClips, script, activeSegmentId, setActiveClip } = useStudioStore();

    const positioned = useMemo(() => withPositions(videoClips), [videoClips]);

    // Mirrors the WaveformVisualizer unmount fix: leaving the studio, or flipping
    // to the Audio tab (which unmounts this component), must stop the audio.
    //
    // A callback ref rather than an unmount effect, because the element is also
    // swapped when `key` changes on a re-assembly — React calls this with null for
    // the outgoing node in both cases, so the element that actually goes away is
    // the one that gets paused. An effect capturing videoRef at mount would hold a
    // stale node after a key change and let the live one keep playing.
    //
    // pause() only — do NOT strip the src attribute. StrictMode's dev double-mount
    // reuses the same DOM node, and React won't re-set an attribute it believes is
    // unchanged, so the player would come back permanently sourceless. Unlike
    // WaveSurfer's WebAudio backend, a media element stops dead on pause.
    const setVideoEl = useCallback((el: HTMLVideoElement | null) => {
        if (!el && videoRef.current) {
            try { videoRef.current.pause(); } catch { /* already stopped */ }
        }
        videoRef.current = el;
    }, []);

    // Clicking a segment seeks the preview, mirroring how it seeks the waveform.
    useEffect(() => {
        if (!activeSegmentId) return;
        const match = positioned.find(p => p.clip.segment_id === activeSegmentId);
        const el = videoRef.current;
        if (!match || !el || !Number.isFinite(el.duration)) return;
        el.currentTime = match.start / 1000;
        setCurrentMs(match.start);
    }, [activeSegmentId, positioned]);

    const activeStripId = positioned.find(p => currentMs >= p.start && currentMs < p.end)?.clip.id ?? null;
    const totalMs = positioned.length ? positioned[positioned.length - 1].end : 0;
    const textFor = (segmentId?: string | null) =>
        script.find(s => s.id === segmentId)?.text ?? '';

    const hasVideo = !!exportState.url;

    // The animatic filename is identical across re-assemblies, so a completed
    // rebuild changes no prop and React never touches the element — the player
    // keeps showing the previous render. Bust the URL with the assembly stamp
    // AND key the element on it, so a fresh <video> mounts and refetches.
    const playerSrc = exportState.url
        ? `${mediaUrl(exportState.url)}${exportState.readyAt ? `?t=${exportState.readyAt}` : ''}`
        : '';

    return (
        <div className="w-full h-full p-4 flex flex-col gap-3">
            {exportState.status === 'failed' && exportState.error && (
                <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2">
                    <AlertCircle className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
                    <p className="flex-1 text-xs text-red-700">{exportState.error}</p>
                    <button
                        onClick={onAssemble}
                        className="flex items-center gap-1 rounded-lg border border-red-200 bg-white px-2 py-1 text-[11px] font-medium text-red-700 hover:bg-red-100 transition-colors"
                    >
                        <RotateCw className="h-3 w-3" />
                        Retry
                    </button>
                </div>
            )}

            {exportState.stale && exportState.status !== 'running' && (
                <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2">
                    <AlertCircle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                    <p className="flex-1 text-xs text-amber-800">
                        This animatic is out of date — the script or narration changed since it was
                        built. Re-assemble to bring the video and captions in line.
                    </p>
                    <button
                        onClick={onAssemble}
                        className="flex items-center gap-1 rounded-lg border border-amber-300 bg-white px-2 py-1 text-[11px] font-medium text-amber-800 hover:bg-amber-100 transition-colors"
                    >
                        <RotateCw className="h-3 w-3" />
                        Re-assemble
                    </button>
                </div>
            )}

            <div className="flex-1 min-h-0 rounded-2xl bg-black/90 flex items-center justify-center overflow-hidden">
                {hasVideo ? (
                    <video
                        ref={setVideoEl}
                        key={playerSrc}
                        data-testid="animatic-player"
                        src={playerSrc}
                        controls
                        playsInline
                        preload="metadata"
                        onTimeUpdate={e => setCurrentMs(e.currentTarget.currentTime * 1000)}
                        className="max-w-full max-h-full"
                    />
                ) : exportState.status === 'running' ? (
                    <div className="flex flex-col items-center gap-3 text-white/80">
                        <Loader2 className="h-8 w-8 animate-spin" />
                        <p className="text-sm">Assembling your animatic...</p>
                    </div>
                ) : (
                    <div className="flex flex-col items-center gap-4 px-8 text-center">
                        <Clapperboard className="h-10 w-10 text-white/30" />
                        <p className="text-sm text-white/60">
                            No animatic yet. Assemble the clips and narration into one video.
                        </p>
                        <button
                            onClick={onAssemble}
                            className="flex items-center gap-2 rounded-xl bg-moore-red px-4 py-2 text-sm font-semibold text-white hover:bg-moore-red-dark transition-all active:scale-[0.98]"
                        >
                            <Film className="h-4 w-4" />
                            Assemble video
                        </button>
                    </div>
                )}
            </div>

            <div className="flex-shrink-0">
                <div className="flex items-center justify-between mb-1.5">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-moore-mid-gray">
                        Clips
                    </p>
                    {totalMs > 0 && (
                        <p className="text-[10px] font-mono text-moore-mid-gray tabular-nums">
                            {formatSeconds(totalMs)} total
                        </p>
                    )}
                </div>
                <div className="flex gap-1 overflow-x-auto pb-1">
                    {positioned.map(({ clip, start, end }, index) => (
                        <button
                            key={clip.id}
                            data-testid="clip-strip-item"
                            data-clip-id={clip.id}
                            title={textFor(clip.segment_id)}
                            onClick={() => {
                                setActiveClip(clip.id);
                                const el = videoRef.current;
                                if (el && Number.isFinite(el.duration)) {
                                    el.currentTime = start / 1000;
                                    setCurrentMs(start);
                                }
                            }}
                            className={`flex-shrink-0 w-24 rounded-lg border px-2 py-1.5 text-left transition-all ${
                                clip.id === activeStripId
                                    ? 'border-moore-red bg-moore-red/10'
                                    : 'border-gray-200 bg-white hover:border-gray-300'
                            }`}
                        >
                            <p className="text-[10px] font-semibold text-moore-dark-gray">
                                Scene {index + 1}
                            </p>
                            <p className="text-[10px] font-mono text-moore-mid-gray tabular-nums">
                                {formatSeconds(end - start)}
                            </p>
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default VideoPreview;
