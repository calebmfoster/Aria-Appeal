"use client"
import * as React from "react"
import { Plus, LogOut, Mic } from "lucide-react"
import { CreateCampaignModal } from "@/components/dashboard/create-campaign-modal"
import { CampaignList } from "@/components/dashboard/CampaignList"
import { VoiceUpload } from "@/components/dashboard/VoiceUpload"
import { VoiceList } from "@/components/dashboard/VoiceList"
import { Modal } from "@/components/ui/modal"
import { useSession, signOut } from "next-auth/react"
import Link from "next/link"

export default function DashboardPage() {
    const [isModalOpen, setIsModalOpen] = React.useState(false)
    const [voiceRefreshKey, setVoiceRefreshKey] = React.useState(0)
    const [campaignRefreshKey, setCampaignRefreshKey] = React.useState(0)
    const [hasCampaigns, setHasCampaigns] = React.useState<boolean | null>(null)
    const [showUploadForm, setShowUploadForm] = React.useState(false)
    const { data: session } = useSession()

    const handleCampaignCreated = () => {
        setCampaignRefreshKey(k => k + 1)
    }

    return (
        <div className="flex flex-col min-h-screen bg-moore-cream text-moore-black">
            {/* Header */}
            <header className="flex h-16 items-center gap-4 border-b border-gray-200 bg-white px-6 shadow-sm">
                <Link href="/dashboard" className="flex items-center gap-2">
                    <span className="text-2xl font-bold tracking-tight">
                        <span className="text-moore-red">M</span>OORE
                    </span>
                    <span className="text-sm font-medium text-moore-mid-gray hidden sm:inline">| Aria Appeal</span>
                </Link>
                <div className="ml-auto flex items-center gap-3">
                    <span className="text-sm text-moore-mid-gray hidden md:inline">
                        {(session?.user as any)?.email || ""}
                    </span>
                    <button
                        onClick={() => signOut({ callbackUrl: "/login" })}
                        className="flex items-center gap-1.5 text-sm text-moore-mid-gray hover:text-moore-red transition-colors"
                    >
                        <LogOut className="h-4 w-4" />
                        <span className="hidden sm:inline">Sign out</span>
                    </button>
                </div>
            </header>

            <main className="flex flex-1 flex-col gap-6 p-6 md:p-8 max-w-7xl mx-auto w-full">
                {/* Page Title */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl md:text-3xl font-semibold text-moore-black tracking-tight">Dashboard</h1>
                        <p className="text-sm text-moore-mid-gray mt-1">Create campaigns and manage your voice profiles.</p>
                    </div>
                    <button
                        onClick={() => setIsModalOpen(true)}
                        className="flex items-center gap-2 rounded-xl bg-moore-red px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-moore-red-dark transition-all active:scale-95"
                    >
                        <Plus className="h-4 w-4" />
                        New Campaign
                    </button>
                </div>

                <div className="grid gap-8 lg:grid-cols-3">
                    {/* Campaigns Section */}
                    <div className="lg:col-span-2 space-y-4">
                        <h2 className="text-sm font-semibold text-moore-dark-gray uppercase tracking-wider">Campaigns</h2>

                        <CampaignList
                            refreshKey={campaignRefreshKey}
                            onEmpty={() => setHasCampaigns(false)}
                            onHasCampaigns={() => setHasCampaigns(true)}
                        />

                        {/* Empty state — shown only when CampaignList reports no campaigns */}
                        {hasCampaigns === false && (
                            <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm flex flex-col items-center justify-center min-h-[240px] text-center">
                                <div className="w-16 h-16 rounded-full bg-moore-red/10 flex items-center justify-center mb-4">
                                    <Mic className="h-8 w-8 text-moore-red" />
                                </div>
                                <h3 className="text-lg font-semibold text-moore-black tracking-tight">No campaigns yet</h3>
                                <p className="text-sm text-moore-mid-gray mt-2 mb-6 max-w-sm">
                                    Create your first campaign to generate a fundraising script and produce studio-quality audio.
                                </p>
                                <button
                                    onClick={() => setIsModalOpen(true)}
                                    className="rounded-xl bg-moore-red px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-moore-red-dark transition-all active:scale-95"
                                >
                                    Create Campaign
                                </button>
                            </div>
                        )}
                    </div>

                    {/* Voice Profiles Sidebar */}
                    <div className="space-y-4">
                        <VoiceList
                            refreshKey={voiceRefreshKey}
                            onAddClick={() => setShowUploadForm(true)}
                        />
                    </div>
                </div>
            </main>

            <CreateCampaignModal
                isOpen={isModalOpen}
                onClose={() => {
                    setIsModalOpen(false)
                    handleCampaignCreated()
                }}
            />

            <Modal
                isOpen={showUploadForm}
                onClose={() => setShowUploadForm(false)}
                title="Add Voice Profile"
            >
                <VoiceUpload
                    bare
                    onUploadSuccess={() => {
                        setVoiceRefreshKey(k => k + 1)
                        setShowUploadForm(false)
                    }}
                />
            </Modal>
        </div>
    )
}
