'use client';

import React from 'react';
import { AudioLines, Clapperboard } from 'lucide-react';
import { useStudioStore } from '@/store/studioStore';
import type { StudioTab } from '@/types/video';

const TABS: { value: StudioTab; label: string; Icon: typeof AudioLines }[] = [
    { value: 'audio', label: 'Audio', Icon: AudioLines },
    { value: 'video', label: 'Video', Icon: Clapperboard },
];

const StudioTabs: React.FC = () => {
    const { medium, activeTab, setActiveTab } = useStudioStore();

    // Audio-only campaigns get no tab bar at all — not a disabled tab, nothing.
    if (medium !== 'video') return null;

    return (
        <div role="tablist" aria-label="Studio medium" className="flex gap-0.5 p-0.5 bg-gray-100 rounded-lg">
            {TABS.map(({ value, label, Icon }) => (
                <button
                    key={value}
                    role="tab"
                    aria-selected={activeTab === value}
                    onClick={() => setActiveTab(value)}
                    className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all ${
                        activeTab === value
                            ? 'bg-white text-moore-black shadow-sm'
                            : 'text-moore-mid-gray hover:text-moore-dark-gray'
                    }`}
                >
                    <Icon className="h-3.5 w-3.5" />
                    {label}
                </button>
            ))}
        </div>
    );
};

export default StudioTabs;
