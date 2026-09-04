'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Loader2, Play, Square } from 'lucide-react';
import { useSession } from 'next-auth/react';
import { API_URL } from '@/lib/config';
import { apiFetch } from '@/lib/api';

interface VoicePreviewButtonProps {
    /** A preset speaker name, or a cloned profile UUID. */
    target: string;
    kind: 'preset' | 'clone';
    /** Already-cached preview URL, if the caller knows one. */
    previewUrl?: string | null;
    /** Caption shown while playing — the English gloss for a non-English voice. */
    caption?: string;
    className?: string;
}

function absolute(url: string): string {
    return url.startsWith('http') ? url : `${API_URL.replace(/\/api\/v1$/, '')}${url}`;
}

export const VoicePreviewButton: React.FC<VoicePreviewButtonProps> = ({
    target, kind, previewUrl, caption, className,
}) => {
    const { data: session } = useSession();
    const [isLoading, setIsLoading] = useState(false);
    const [isPlaying, setIsPlaying] = useState(false);
    const [url, setUrl] = useState<string | null>(previewUrl ?? null);
    const audioRef = useRef<HTMLAudioElement | null>(null);

    useEffect(() => {
        setUrl(previewUrl ?? null);
    }, [previewUrl, target]);

    const stop = () => {
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current = null;
        }
        setIsPlaying(false);
    };

    // Mirrors the studio's teardown rule: unmounting must stop playback.
    useEffect(() => stop, []);

    const play = (src: string) => {
        stop();
        const audio = new Audio(absolute(src));
        audio.onended = () => setIsPlaying(false);
        audio.onerror = () => setIsPlaying(false);
        audio.play().catch(() => setIsPlaying(false));
        audioRef.current = audio;
        setIsPlaying(true);
    };

    const handleClick = async (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();

        if (isPlaying) {
            stop();
            return;
        }
        if (url) {
            play(url);
            return;
        }

        setIsLoading(true);
        try {
            const path = kind === 'preset'
                ? `/voice-profiles/presets/${target}/preview`
                : `/voice-profiles/${target}/preview`;
            const res = await apiFetch(path, { method: 'POST', token: session?.accessToken });
            if (!res.ok) return;
            const data = await res.json();
            if (data.preview_url) {
                setUrl(data.preview_url);
                play(data.preview_url);
            }
        } catch {
            /* leave the button idle; the user can retry */
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <span className={`inline-flex items-center gap-1.5 ${className ?? ''}`}>
            <button
                type="button"
                onClick={handleClick}
                aria-label={isPlaying ? `Stop preview of ${target}` : `Preview ${target}`}
                disabled={isLoading}
                className={`h-8 w-8 rounded-full flex items-center justify-center transition-colors flex-shrink-0 ${
                    isPlaying
                        ? 'text-moore-red bg-moore-red/10'
                        : 'text-moore-mid-gray hover:text-moore-red hover:bg-moore-red/10'
                } disabled:opacity-50`}
            >
                {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    : isPlaying ? <Square className="w-3.5 h-3.5" />
                    : <Play className="w-3.5 h-3.5" />}
            </button>
            {isPlaying && caption && (
                <span className="text-[10px] text-moore-mid-gray italic truncate">&ldquo;{caption}&rdquo;</span>
            )}
        </span>
    );
};

export default VoicePreviewButton;
