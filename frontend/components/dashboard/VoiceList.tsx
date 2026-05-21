'use client';

import React, { useEffect, useState, useRef } from 'react';
import { API_URL } from '@/lib/config';
import { apiFetch } from '@/lib/api';
import { Trash2, Mic, Play, Square, Loader2, Plus } from 'lucide-react';
import { useSession } from 'next-auth/react';
import type { VoiceProfile } from '@/types/studio';

interface Campaign {
    id: string;
    title: string;
    segments: { voice_profile_id?: string | null }[];
}

interface VoiceListProps {
    refreshKey?: number;
    onAddClick?: () => void;
}

export const VoiceList: React.FC<VoiceListProps> = ({ refreshKey, onAddClick }) => {
    const [profiles, setProfiles] = useState<VoiceProfile[]>([]);
    const [campaigns, setCampaigns] = useState<Campaign[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [playingId, setPlayingId] = useState<string | null>(null);
    const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editingName, setEditingName] = useState('');
    const audioRef = useRef<HTMLAudioElement | null>(null);
    const editInputRef = useRef<HTMLInputElement | null>(null);
    const { data: session, status } = useSession();

    const fetchProfiles = async () => {
        try {
            const [profilesRes, campaignsRes] = await Promise.all([
                apiFetch('/voice-profiles/', { token: session?.accessToken }),
                apiFetch('/projects', { token: session?.accessToken }),
            ]);
            if (profilesRes.ok) {
                const data = await profilesRes.json();
                setProfiles(data);
            }
            if (campaignsRes.ok) {
                const data = await campaignsRes.json();
                setCampaigns(data);
            }
        } catch (error) {
            console.error('Error fetching voice profiles:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const deleteProfile = async (id: string) => {
        try {
            const response = await apiFetch(`/voice-profiles/${id}`, { method: 'DELETE', token: session?.accessToken });
            if (response.ok) {
                if (playingId === id) stopPlayback();
                setProfiles(profiles.filter(p => p.id !== id));
            } else {
                const errorData = await response.text();
                console.error('Delete failed:', response.status, errorData);
            }
        } catch (error) {
            console.error('Error deleting profile:', error);
        }
    };

    const startEdit = (profile: VoiceProfile) => {
        setEditingId(profile.id);
        setEditingName(profile.name);
        setTimeout(() => editInputRef.current?.select(), 0);
    };

    const commitEdit = async () => {
        if (!editingId) return;
        const trimmed = editingName.trim();
        const original = profiles.find(p => p.id === editingId)?.name ?? '';

        setEditingId(null);

        if (!trimmed || trimmed === original) return;

        try {
            const response = await apiFetch(`/voice-profiles/${editingId}`, {
                method: 'PATCH',
                token: session?.accessToken,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: trimmed }),
            });
            if (response.ok) {
                const updated: VoiceProfile = await response.json();
                setProfiles(prev => prev.map(p => p.id === updated.id ? updated : p));
            } else {
                console.error('Rename failed:', response.status);
            }
        } catch (error) {
            console.error('Error renaming profile:', error);
        }
    };

    const cancelEdit = () => {
        setEditingId(null);
        setEditingName('');
    };

    const togglePlayback = (profile: VoiceProfile) => {
        if (playingId === profile.id) {
            stopPlayback();
            return;
        }

        stopPlayback();

        if (!profile.preview_url) return;

        const url = profile.preview_url.startsWith('http')
            ? profile.preview_url
            : `${API_URL.replace('/api/v1', '')}${profile.preview_url}`;

        const audio = new Audio(url);
        audio.onended = () => setPlayingId(null);
        audio.onerror = () => setPlayingId(null);
        audio.play();
        audioRef.current = audio;
        setPlayingId(profile.id);
    };

    const stopPlayback = () => {
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current = null;
        }
        setPlayingId(null);
    };

    const getCampaignUsage = (profileId: string): string[] => {
        return campaigns
            .filter(c => c.segments.some(s => s.voice_profile_id === profileId))
            .map(c => c.title);
    };

    useEffect(() => {
        if (status === 'authenticated' && session) {
            fetchProfiles();
        } else if (status === 'unauthenticated') {
            setIsLoading(false);
        }
    }, [status, session, refreshKey]);

    useEffect(() => {
        return () => stopPlayback();
    }, []);

    if (isLoading) {
        return (
            <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
                <div className="flex items-center gap-2 text-moore-mid-gray">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-sm">Loading voice profiles...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-moore-black tracking-tight flex items-center gap-2">
                    <Mic className="w-5 h-5 text-moore-red" />
                    Your Voice Profiles
                </h3>
                {onAddClick && (
                    <button
                        onClick={onAddClick}
                        className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium text-moore-mid-gray border border-gray-200 hover:text-moore-red hover:border-moore-red transition-colors"
                    >
                        <Plus className="w-3.5 h-3.5" />
                        Add
                    </button>
                )}
            </div>
            {profiles.length === 0 ? (
                <p className="text-sm text-moore-mid-gray italic">No voice profiles added yet.</p>
            ) : (
                <div className="grid gap-2">
                    {profiles.map((profile) => {
                        const usedIn = getCampaignUsage(profile.id);
                        return (
                            <div
                                key={profile.id}
                                className="flex items-center justify-between p-3 bg-moore-cream/50 border border-gray-100 rounded-xl hover:bg-moore-cream transition-colors"
                            >
                                <div className="flex items-center gap-3">
                                    {profile.has_cloned_voice && profile.preview_url && (
                                        <button
                                            onClick={() => togglePlayback(profile)}
                                            className={`h-8 w-8 rounded-full flex items-center justify-center transition-colors ${
                                                playingId === profile.id
                                                    ? 'text-moore-red bg-moore-red/10'
                                                    : 'text-moore-mid-gray hover:text-moore-red hover:bg-moore-red/10'
                                            }`}
                                        >
                                            {playingId === profile.id ? (
                                                <Square className="w-3.5 h-3.5" />
                                            ) : (
                                                <Play className="w-3.5 h-3.5" />
                                            )}
                                        </button>
                                    )}
                                    <div>
                                        <div className="flex items-center gap-2">
                                            {editingId === profile.id ? (
                                                <input
                                                    ref={editInputRef}
                                                    value={editingName}
                                                    onChange={e => setEditingName(e.target.value)}
                                                    onBlur={commitEdit}
                                                    onKeyDown={e => {
                                                        if (e.key === 'Enter') { e.preventDefault(); commitEdit(); }
                                                        if (e.key === 'Escape') { e.preventDefault(); cancelEdit(); }
                                                    }}
                                                    className="font-medium text-moore-black text-sm bg-white border border-moore-red/40 rounded px-1.5 py-0.5 outline-none focus:ring-1 focus:ring-moore-red/30 w-40"
                                                />
                                            ) : (
                                                <p
                                                    className="font-medium text-moore-black text-sm cursor-text hover:underline decoration-dotted underline-offset-2"
                                                    onClick={() => startEdit(profile)}
                                                    title="Click to rename"
                                                >
                                                    {profile.name}
                                                </p>
                                            )}
                                            {profile.has_cloned_voice && (
                                                <span className="px-1.5 py-0.5 text-[10px] font-semibold uppercase bg-moore-red/10 text-moore-red border border-moore-red/20 rounded-md">
                                                    Cloned
                                                </span>
                                            )}
                                        </div>
                                        <p className="text-xs text-moore-mid-gray">{profile.base_model}</p>
                                        {usedIn.length > 0 ? (
                                            <p className="text-[11px] text-moore-mid-gray mt-0.5">
                                                Used in: {usedIn.join(', ')}
                                            </p>
                                        ) : (
                                            <span className="inline-block mt-0.5 px-1.5 py-0.5 text-[10px] font-medium bg-gray-100 text-gray-400 rounded">
                                                Unused
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <button
                                    onClick={() => setConfirmDeleteId(profile.id)}
                                    className="h-8 w-8 rounded-full flex items-center justify-center text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Delete Confirmation Modal */}
            {confirmDeleteId && (() => {
                const profile = profiles.find(p => p.id === confirmDeleteId);
                if (!profile) return null;
                return (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setConfirmDeleteId(null)}>
                        <div className="bg-white rounded-2xl p-6 shadow-xl max-w-sm w-full mx-4" onClick={(e) => e.stopPropagation()}>
                            <h3 className="text-lg font-semibold text-moore-black mb-2">Delete Voice Profile</h3>
                            <p className="text-sm text-moore-mid-gray mb-5">
                                Delete <span className="font-medium text-moore-dark-gray">{profile.name}</span>? This cannot be undone.
                            </p>
                            <div className="flex gap-2 justify-end">
                                <button
                                    onClick={() => setConfirmDeleteId(null)}
                                    className="rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-moore-dark-gray hover:bg-gray-50 transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={() => {
                                        deleteProfile(confirmDeleteId);
                                        setConfirmDeleteId(null);
                                    }}
                                    className="flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 transition-colors"
                                >
                                    <Trash2 className="w-3.5 h-3.5" />
                                    Delete
                                </button>
                            </div>
                        </div>
                    </div>
                );
            })()}
        </div>
    );
};
