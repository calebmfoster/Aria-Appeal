'use client';

import React from 'react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export default function StudioPage() {
    return (
        <div className="flex h-screen w-full bg-moore-cream items-center justify-center flex-col gap-4">
            <h1 className="text-2xl font-semibold text-moore-black">
                <span className="text-moore-red">M</span>OORE Studio
            </h1>
            <p className="text-moore-mid-gray text-sm">
                Please open a project from the dashboard to use the studio editor.
            </p>
            <Link
                href="/dashboard"
                className="flex items-center gap-2 mt-4 rounded-xl bg-moore-red px-5 py-2.5 text-sm font-semibold text-white hover:bg-moore-red-dark transition-all"
            >
                <ArrowLeft className="h-4 w-4" />
                Go to Dashboard
            </Link>
        </div>
    );
}
