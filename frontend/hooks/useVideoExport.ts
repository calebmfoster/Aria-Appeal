'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { apiFetch } from '@/lib/api';
import type { VideoExportState } from '@/types/video';
import { IDLE_EXPORT } from '@/types/video';

const POLL_MS = 2000;

export function useVideoExport(projectId: string | undefined, token: string | undefined) {
    const [state, setState] = useState<VideoExportState>(IDLE_EXPORT);
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const aliveRef = useRef(true);

    useEffect(() => {
        aliveRef.current = true;
        return () => {
            aliveRef.current = false;
            if (timerRef.current) clearTimeout(timerRef.current);
            timerRef.current = null;
        };
    }, []);

    const readStatus = useCallback(async (): Promise<VideoExportState | null> => {
        if (!projectId || !token) return null;
        const res = await apiFetch(`/projects/${projectId}/video/export`, { token });
        if (!res.ok) return null;
        const body = await res.json();
        return {
            status: body.status ?? 'idle',
            url: body.video_master_url ?? null,
            error: body.error ?? null,
        };
    }, [projectId, token]);

    // A failed assembly must leave any previous animatic playable, so a null
    // url from the server never overwrites a url we already hold.
    const merge = useCallback((next: VideoExportState) => {
        setState(prev => ({ ...next, url: next.url ?? prev.url }));
    }, []);

    const refresh = useCallback(async () => {
        const next = await readStatus();
        if (next && aliveRef.current) merge(next);
    }, [readStatus, merge]);

    const poll = useCallback(() => {
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(async () => {
            if (!aliveRef.current) return;
            const next = await readStatus();
            if (!aliveRef.current) return;
            if (next) {
                merge(next);
                if (next.status === 'running') poll();
            } else {
                poll();
            }
        }, POLL_MS);
    }, [readStatus, merge]);

    const assemble = useCallback(async () => {
        if (!projectId || !token) return;
        setState(prev => ({ status: 'running', url: prev.url, error: null }));
        try {
            const res = await apiFetch(`/projects/${projectId}/video/export`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                token,
            });
            if (!res.ok) {
                const body = await res.json().catch(() => ({}));
                const detail = typeof body?.detail === 'string'
                    ? body.detail
                    : 'Assembly could not be started.';
                if (aliveRef.current) {
                    setState(prev => ({ status: 'failed', url: prev.url, error: detail }));
                }
                return;
            }
            if (aliveRef.current) poll();
        } catch (e: any) {
            if (aliveRef.current) {
                setState(prev => ({ status: 'failed', url: prev.url, error: e?.message ?? 'Assembly failed.' }));
            }
        }
    }, [projectId, token, poll]);

    return { state, assemble, refresh };
}
