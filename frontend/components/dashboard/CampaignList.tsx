'use client';

import React, { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/api';
import { Loader2, Mic, MoreVertical, Trash2, AudioLines, FileText } from 'lucide-react';
import toast from 'react-hot-toast';

interface Campaign {
    id: string;
    title: string;
    status: 'draft' | 'generated' | 'mastered';
    created_at: string | null;
    target_audience: { audience?: string; emotion?: string };
    segments: { id: string; audio_url?: string; start_time_ms?: number; end_time_ms?: number }[];
}

interface CampaignListProps {
    refreshKey: number;
    onEmpty: () => void;
    onHasCampaigns: () => void;
}

const statusConfig = {
    draft: { label: 'Draft', color: 'bg-gray-100 text-gray-600' },
    generated: { label: 'Generated', color: 'bg-blue-50 text-blue-600' },
    mastered: { label: 'Mastered', color: 'bg-green-50 text-green-700' },
};

export const CampaignList: React.FC<CampaignListProps> = ({ refreshKey, onEmpty, onHasCampaigns }) => {
    const [campaigns, setCampaigns] = useState<Campaign[]>([]);
    const [loading, setLoading] = useState(true);
    const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
    const [deletingId, setDeletingId] = useState<string | null>(null);
    const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
    const { data: session } = useSession();
    const router = useRouter();

    const fetchCampaigns = async () => {
        const token = session?.accessToken;
        if (!token) return;

        try {
            const res = await apiFetch('/projects', { token });
            if (!res.ok) throw new Error('Failed to fetch');
            const data: Campaign[] = await res.json();
            setCampaigns(data);
            if (data.length === 0) onEmpty();
            else onHasCampaigns();
        } catch {
            toast.error('Failed to load campaigns');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (session) fetchCampaigns();
    }, [session, refreshKey]);

    const handleDelete = async (id: string) => {
        const token = session?.accessToken;
        if (!token) return;

        setDeletingId(id);
        try {
            const res = await apiFetch(`/projects/${id}`, { method: 'DELETE', token });
            if (!res.ok) throw new Error('Delete failed');
            setCampaigns((prev) => prev.filter((c) => c.id !== id));
            toast.success('Campaign deleted');
            if (campaigns.length <= 1) onEmpty();
        } catch {
            toast.error('Failed to delete campaign');
        } finally {
            setDeletingId(null);
            setMenuOpenId(null);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[200px]">
                <Loader2 className="h-6 w-6 animate-spin text-moore-red" />
            </div>
        );
    }

    if (campaigns.length === 0) return null;

    const confirmCampaign = campaigns.find(c => c.id === confirmDeleteId);

    return (
        <div className="space-y-3">
            {/* Delete Confirmation Modal */}
            {confirmDeleteId && confirmCampaign && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setConfirmDeleteId(null)}>
                    <div className="bg-white rounded-2xl p-6 shadow-xl max-w-sm w-full mx-4" onClick={(e) => e.stopPropagation()}>
                        <h3 className="text-lg font-semibold text-moore-black mb-2">Delete Campaign</h3>
                        <p className="text-sm text-moore-mid-gray mb-5">
                            Delete <span className="font-medium text-moore-dark-gray">{confirmCampaign.title}</span>? All audio and script data will be permanently removed.
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
                                    handleDelete(confirmDeleteId);
                                    setConfirmDeleteId(null);
                                }}
                                disabled={deletingId === confirmDeleteId}
                                className="flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 transition-colors disabled:opacity-50"
                            >
                                {deletingId === confirmDeleteId ? (
                                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                ) : (
                                    <Trash2 className="h-3.5 w-3.5" />
                                )}
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {campaigns.map((campaign) => {
                const status = statusConfig[campaign.status] || statusConfig.draft;
                const segmentCount = campaign.segments?.length || 0;
                const audioReady = campaign.segments?.filter((s) => s.audio_url).length || 0;
                const audioPercent = segmentCount > 0 ? (audioReady / segmentCount) * 100 : 0;

                const totalDurationMs = campaign.status === 'mastered'
                    ? Math.max(0, ...campaign.segments.map((s) => s.end_time_ms ?? 0))
                    : 0;
                const totalSecs = Math.round(totalDurationMs / 1000);
                const durationLabel = totalSecs > 0
                    ? `${Math.floor(totalSecs / 60)}:${String(totalSecs % 60).padStart(2, '0')}`
                    : null;

                const date = campaign.created_at
                    ? new Date(campaign.created_at).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                      })
                    : null;

                return (
                    <div
                        key={campaign.id}
                        onClick={() => router.push(`/dashboard/studio/${campaign.id}`)}
                        className="relative flex items-center gap-4 rounded-xl border border-gray-200 bg-white p-4 shadow-sm cursor-pointer hover:border-moore-red/30 hover:shadow-md transition-all group"
                    >
                        <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-moore-red/10 flex items-center justify-center">
                            <AudioLines className="h-5 w-5 text-moore-red" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                                <h4 className="text-sm font-semibold text-moore-black truncate">
                                    {campaign.title}
                                </h4>
                                <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${status.color}`}>
                                    {status.label}
                                </span>
                            </div>
                            <div className="flex items-center gap-3 mt-1 text-[11px] text-moore-mid-gray">
                                {date && <span>{date}</span>}
                                <span className="flex items-center gap-1">
                                    <FileText className="h-3 w-3" />
                                    {segmentCount} segments
                                </span>
                                {audioReady > 0 && (
                                    <span className="flex items-center gap-1.5">
                                        <Mic className="h-3 w-3 flex-shrink-0" />
                                        <span className="flex items-center gap-1">
                                            <div className="w-16 h-1.5 rounded-full bg-gray-200 overflow-hidden">
                                                <div
                                                    className="h-full rounded-full bg-moore-red/70 transition-all"
                                                    style={{ width: `${audioPercent}%` }}
                                                />
                                            </div>
                                            <span>{audioReady}/{segmentCount}</span>
                                        </span>
                                    </span>
                                )}
                                {durationLabel && (
                                    <span className="flex items-center gap-1">
                                        <AudioLines className="h-3 w-3" />
                                        {durationLabel}
                                    </span>
                                )}
                            </div>
                        </div>
                        <div className="relative">
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setMenuOpenId(menuOpenId === campaign.id ? null : campaign.id);
                                }}
                                className="p-1.5 rounded-lg hover:bg-gray-100 text-moore-mid-gray opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                                <MoreVertical className="h-4 w-4" />
                            </button>
                            {menuOpenId === campaign.id && (
                                <div className="absolute right-0 top-8 z-10 w-36 rounded-xl border border-gray-200 bg-white shadow-lg py-1">
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            setConfirmDeleteId(campaign.id);
                                            setMenuOpenId(null);
                                        }}
                                        className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                                    >
                                        <Trash2 className="h-3.5 w-3.5" />
                                        Delete
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                );
            })}
        </div>
    );
};
