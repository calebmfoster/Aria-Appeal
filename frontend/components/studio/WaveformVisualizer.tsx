'use client';

import React, { useEffect, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.js';
import { useStudioStore } from '@/store/studioStore';
import { API_URL } from '@/lib/config';
import { Play, Pause } from 'lucide-react';

function formatWaveformTime(seconds: number): string {
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return `${min}:${sec.toString().padStart(2, '0')}`;
}

const WaveformVisualizer: React.FC = () => {
    const containerRef = useRef<HTMLDivElement>(null);
    const wavesurferRef = useRef<WaveSurfer | null>(null);
    const regionsPluginRef = useRef<RegionsPlugin | null>(null);

    const {
        audioUrl,
        script,
        isPlaying,
        activeSegmentId,
        currentTime,
        duration,
        setCurrentTime,
        setDuration,
        setIsPlaying,
        setActiveSegment,
        updateSegment
    } = useStudioStore();

    // Initialize WaveSurfer
    useEffect(() => {
        if (!containerRef.current) return;

        let destroyed = false;

        const ws = WaveSurfer.create({
            container: containerRef.current,
            waveColor: '#E0261C40',
            progressColor: '#E0261C',
            cursorColor: '#333333',
            barWidth: 2,
            barGap: 1,
            barRadius: 2,
            height: 128,
            normalize: true,
            backend: 'WebAudio',
        });

        const wsRegions = RegionsPlugin.create();
        ws.registerPlugin(wsRegions);

        wavesurferRef.current = ws;
        regionsPluginRef.current = wsRegions;

        ws.on('ready', () => {
            if (destroyed) return;
            const currentDuration = ws.getDuration();
            setDuration(currentDuration);

            const state = useStudioStore.getState();
            if (!state.audioUrl && state.activeSegmentId) {
                const activeSegment = state.script.find(s => s.id === state.activeSegmentId);
                if (activeSegment) {
                    const expectedEndMs = Math.round(activeSegment.start_ms + (currentDuration * 1000));
                    if (activeSegment.end_ms !== expectedEndMs) {
                        state.updateSegment(state.activeSegmentId, { end_ms: expectedEndMs });
                    }
                }
            }
        });

        ws.on('audioprocess', (currentTime) => {
            if (!destroyed) setCurrentTime(currentTime);
        });

        ws.on('interaction', () => {
            if (!destroyed) setCurrentTime(ws.getCurrentTime());
        });

        ws.on('play', () => {
            if (!destroyed) useStudioStore.getState().setIsPlaying(true);
        });

        ws.on('pause', () => {
            if (!destroyed) useStudioStore.getState().setIsPlaying(false);
        });

        ws.on('finish', () => {
            if (!destroyed) {
                useStudioStore.getState().setIsPlaying(false);
                ws.seekTo(0);
            }
        });

        ws.on('error', (err: Error) => {
            if (err?.name === 'AbortError') return;
            console.error('WaveSurfer error:', err);
        });

        wsRegions.on('region-clicked', (region, e) => {
            e.stopPropagation();
            if (!destroyed) {
                setActiveSegment(region.id);
                region.play();
            }
        });

        return () => {
            destroyed = true;
            try {
                ws.destroy();
            } catch {
                // Ignore AbortError during React strict mode double-mount cleanup
            }
        };
    }, []);

    const getFullAudioUrl = (url: string) => {
        if (!url) return '';
        if (url.startsWith('http')) return url;
        const baseUrl = API_URL.replace(/\/api\/v1$/, '');
        return `${baseUrl}${url}`;
    };

    // Load Audio
    useEffect(() => {
        if (wavesurferRef.current) {
            if (audioUrl) {
                wavesurferRef.current.load(getFullAudioUrl(audioUrl));
            } else if (activeSegmentId) {
                const activeSegment = script.find(s => s.id === activeSegmentId);
                if (activeSegment?.audio_url) {
                    wavesurferRef.current.load(getFullAudioUrl(activeSegment.audio_url));
                } else {
                    wavesurferRef.current.empty();
                }
            } else {
                wavesurferRef.current.empty();
            }
        }
    }, [audioUrl, activeSegmentId, script]);

    // Construct Regions from Script
    useEffect(() => {
        if (!regionsPluginRef.current || !script.length) return;

        const regions = regionsPluginRef.current;
        regions.clearRegions();

        script.forEach((segment) => {
            regions.addRegion({
                id: segment.id,
                start: segment.start_ms / 1000,
                end: segment.end_ms / 1000,
                color: segment.id === activeSegmentId ? 'rgba(224, 38, 28, 0.15)' : 'rgba(224, 38, 28, 0.05)',
                drag: false,
                resize: false,
            });
        });
    }, [script, activeSegmentId]);

    // Handle Playback State Sync
    useEffect(() => {
        const ws = wavesurferRef.current;
        if (!ws) return;

        if (isPlaying && !ws.isPlaying()) {
            ws.play();
        } else if (!isPlaying && ws.isPlaying()) {
            ws.pause();
        }
    }, [isPlaying]);

    // Seek to segment when clicking in ScriptEditor
    useEffect(() => {
        const ws = wavesurferRef.current;
        if (!ws || !activeSegmentId) return;

        const activeSegment = script.find(s => s.id === activeSegmentId);
        if (!activeSegment) return;

        const duration = ws.getDuration();
        if (duration > 0 && audioUrl) {
            const seekPosition = (activeSegment.start_ms / 1000) / duration;
            if (seekPosition >= 0 && seekPosition <= 1) {
                ws.seekTo(seekPosition);
            }
        }
    }, [activeSegmentId]);

    const activeSegmentAudioLoaded = !!script.find(s => s.id === activeSegmentId)?.audio_url;
    const hasAudioToPlay = !!audioUrl || activeSegmentAudioLoaded;

    return (
        <div className="w-full h-full p-4 bg-white rounded-2xl border border-gray-100 flex flex-col justify-center">
            <div ref={containerRef} className="w-full" />

            {/* Time Display + Playback Controls */}
            <div className="flex justify-center items-center gap-4 mt-6">
                <span className="text-xs font-mono text-moore-mid-gray w-16 text-right tabular-nums">
                    {formatWaveformTime(currentTime)}
                </span>
                <button
                    disabled={!hasAudioToPlay}
                    onClick={() => setIsPlaying(!isPlaying)}
                    className={`h-11 w-11 rounded-full flex items-center justify-center transition-all ${
                        hasAudioToPlay
                            ? 'bg-moore-red text-white hover:bg-moore-red-dark shadow-sm active:scale-95'
                            : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    }`}
                >
                    {isPlaying ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5 ml-0.5" />}
                </button>
                <span className="text-xs font-mono text-moore-mid-gray w-16 tabular-nums">
                    {formatWaveformTime(duration)}
                </span>
            </div>

            {(!audioUrl && !activeSegmentAudioLoaded) && (
                <div className="text-center text-moore-mid-gray text-sm mt-3">
                    No audio loaded. Select a segment or generate audio.
                </div>
            )}
        </div>
    );
};

export default WaveformVisualizer;
