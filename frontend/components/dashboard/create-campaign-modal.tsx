"use client"
import * as React from "react"
import { Modal } from "@/components/ui/modal"
import { Input } from "@/components/ui/input"
import { useSession } from "next-auth/react"
import { API_URL } from "@/lib/config"
import toast from 'react-hot-toast'
import { ChevronDown, Loader2, Sparkles, FileText } from "lucide-react"
import { Textarea } from "@/components/ui/textarea"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"

interface CreateCampaignModalProps {
    isOpen: boolean
    onClose: () => void
}

const STEPS = [
    "Crafting your script...",
    "Saving campaign...",
    "Opening studio..."
]

export function CreateCampaignModal({ isOpen, onClose }: CreateCampaignModalProps) {
    const { data: session } = useSession();
    const [loading, setLoading] = React.useState(false)
    const [step, setStep] = React.useState(0)
    const [mode, setMode] = React.useState<'ai' | 'custom'>('ai')
    const [showAdvanced, setShowAdvanced] = React.useState(false)
    const [formData, setFormData] = React.useState({
        target_audience: "",
        cause: "",
        primary_emotion: "",
        custom_script: "",
        organization_name: "",
        story_hook: "",
        script_length: "30s",
        messaging_strategy: "",
        ask_amount: "",
    })

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value })
    }

    const handleSelectChange = (name: string, value: string) => {
        setFormData({ ...formData, [name]: value })
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)
        setStep(0)
        try {
            const payload: Record<string, string> = {
                cause: formData.cause,
                target_audience: formData.target_audience || 'General',
                primary_emotion: formData.primary_emotion || 'Compelling',
                script_length: formData.script_length || '30s',
            };
            if (mode === 'custom' && formData.custom_script.trim()) {
                payload.custom_script = formData.custom_script;
            }
            if (mode === 'ai') {
                if (formData.organization_name.trim()) payload.organization_name = formData.organization_name.trim();
                if (formData.story_hook.trim()) payload.story_hook = formData.story_hook.trim();
                if (formData.messaging_strategy) payload.messaging_strategy = formData.messaging_strategy;
                if (formData.ask_amount.trim()) payload.ask_amount = formData.ask_amount.trim();
            }

            const res = await fetch(`${API_URL}/projects`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${session?.accessToken}`
                },
                body: JSON.stringify(payload),
            })

            if (!res.ok) {
                const errData = await res.json().catch(() => null)
                const detail = errData?.detail || "Failed to generate script"
                throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
            }

            setStep(1)
            const data = await res.json()

            setStep(2)
            window.location.href = `/dashboard/studio/${data.id}`
        } catch (error: any) {
            console.error(error)
            toast.error(error.message || "Error generating script. Ensure backend is running.")
            setLoading(false)
            setStep(0)
        }
    }

    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Start New Campaign">
            <form onSubmit={handleSubmit} className="space-y-4">
                {/* Mode Toggle */}
                <div className="flex gap-2 p-1 bg-gray-100 rounded-xl">
                    <button
                        type="button"
                        onClick={() => setMode('ai')}
                        className={`flex-1 flex items-center justify-center gap-1.5 rounded-lg py-2 text-sm font-medium transition-all ${
                            mode === 'ai' ? 'bg-white text-moore-black shadow-sm' : 'text-moore-mid-gray hover:text-moore-dark-gray'
                        }`}
                    >
                        <Sparkles className="h-3.5 w-3.5" />
                        Generate with AI
                    </button>
                    <button
                        type="button"
                        onClick={() => setMode('custom')}
                        className={`flex-1 flex items-center justify-center gap-1.5 rounded-lg py-2 text-sm font-medium transition-all ${
                            mode === 'custom' ? 'bg-white text-moore-black shadow-sm' : 'text-moore-mid-gray hover:text-moore-dark-gray'
                        }`}
                    >
                        <FileText className="h-3.5 w-3.5" />
                        Paste Your Own
                    </button>
                </div>

                {/* Core Cause / Campaign Title */}
                <div className="space-y-1.5">
                    <label htmlFor="cause" className="text-sm font-medium text-moore-dark-gray">
                        {mode === 'custom' ? 'Campaign Title' : 'Core Cause'}
                    </label>
                    <Input
                        id="cause"
                        name="cause"
                        placeholder={mode === 'custom' ? 'e.g. Spring Fundraiser 2026' : 'e.g. Clean Water Initiative'}
                        required
                        value={formData.cause}
                        onChange={handleChange}
                        className="rounded-xl border-gray-200 focus:ring-2 focus:ring-moore-red/30 focus:border-moore-red"
                    />
                </div>

                {/* Custom script textarea */}
                {mode === 'custom' && (
                    <div className="space-y-1.5">
                        <label htmlFor="custom_script" className="text-sm font-medium text-moore-dark-gray">Script</label>
                        <Textarea
                            id="custom_script"
                            name="custom_script"
                            placeholder={"Paste your script here.\n\nSeparate segments with blank lines, or write continuous text and we'll split by sentence."}
                            required
                            rows={6}
                            value={formData.custom_script}
                            onChange={handleChange}
                            className="rounded-xl border-gray-200 focus:ring-2 focus:ring-moore-red/30 focus:border-moore-red text-sm"
                        />
                    </div>
                )}

                {/* Target Audience & Primary Emotion (shown in both modes) */}
                <div className="space-y-1.5">
                    <label htmlFor="target_audience" className="text-sm font-medium text-moore-dark-gray">Target Audience</label>
                    <Input
                        id="target_audience"
                        name="target_audience"
                        placeholder="e.g. Young Professionals"
                        required={mode === 'ai'}
                        value={formData.target_audience}
                        onChange={handleChange}
                        className="rounded-xl border-gray-200 focus:ring-2 focus:ring-moore-red/30 focus:border-moore-red"
                    />
                </div>
                <div className="space-y-1.5">
                    <label htmlFor="primary_emotion" className="text-sm font-medium text-moore-dark-gray">Primary Emotion</label>
                    <Input
                        id="primary_emotion"
                        name="primary_emotion"
                        placeholder="e.g. Hopeful, Urgent"
                        required={mode === 'ai'}
                        value={formData.primary_emotion}
                        onChange={handleChange}
                        className="rounded-xl border-gray-200 focus:ring-2 focus:ring-moore-red/30 focus:border-moore-red"
                    />
                </div>

                {/* Advanced / More Context section (AI mode only) */}
                {mode === 'ai' && (
                    <div className="border-t border-gray-100 pt-3">
                        <button
                            type="button"
                            onClick={() => setShowAdvanced(v => !v)}
                            className="flex items-center gap-1.5 text-xs text-moore-mid-gray hover:text-moore-dark-gray transition-colors"
                        >
                            <ChevronDown className={`h-3 w-3 transition-transform duration-200 ${showAdvanced ? 'rotate-180' : ''}`} />
                            {showAdvanced ? 'Hide extra context' : 'Add more context'} <span className="text-moore-mid-gray/60">(optional)</span>
                        </button>

                        {showAdvanced && (
                            <div className="mt-3 space-y-3">
                                {/* Organization Name */}
                                <div className="space-y-1.5">
                                    <label className="text-sm font-medium text-moore-dark-gray">Organization Name</label>
                                    <Input
                                        name="organization_name"
                                        placeholder="e.g. Clean Water Partners"
                                        value={formData.organization_name}
                                        onChange={handleChange}
                                        className="rounded-xl border-gray-200 focus:ring-2 focus:ring-moore-red/30 focus:border-moore-red"
                                    />
                                </div>

                                {/* Story Hook */}
                                <div className="space-y-1.5">
                                    <label className="text-sm font-medium text-moore-dark-gray">
                                        Story Hook{" "}
                                        <span className="font-normal text-moore-mid-gray">— a specific detail to anchor the script</span>
                                    </label>
                                    <Textarea
                                        name="story_hook"
                                        rows={2}
                                        placeholder="e.g. A family in rural Kenya walks 3 miles for dirty water every day."
                                        value={formData.story_hook}
                                        onChange={handleChange}
                                        className="rounded-xl border-gray-200 focus:ring-2 focus:ring-moore-red/30 focus:border-moore-red text-sm"
                                    />
                                </div>

                                {/* Script Length + Ask Amount */}
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="space-y-1.5">
                                        <label className="text-sm font-medium text-moore-dark-gray">Script Length</label>
                                        <Select
                                            value={formData.script_length}
                                            onValueChange={v => handleSelectChange('script_length', v)}
                                        >
                                            <SelectTrigger className="rounded-xl border-gray-200">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="30s">30s (~70 words)</SelectItem>
                                                <SelectItem value="60s">60s (~140 words)</SelectItem>
                                                <SelectItem value="90s">90s (~210 words)</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-1.5">
                                        <label className="text-sm font-medium text-moore-dark-gray">Ask Amount</label>
                                        <Input
                                            name="ask_amount"
                                            placeholder="e.g. $50 or $25/month"
                                            value={formData.ask_amount}
                                            onChange={handleChange}
                                            className="rounded-xl border-gray-200 focus:ring-2 focus:ring-moore-red/30 focus:border-moore-red"
                                        />
                                    </div>
                                </div>

                                {/* Messaging Strategy */}
                                <div className="space-y-1.5">
                                    <label className="text-sm font-medium text-moore-dark-gray">Messaging Strategy</label>
                                    <Select
                                        value={formData.messaging_strategy}
                                        onValueChange={v => handleSelectChange('messaging_strategy', v)}
                                    >
                                        <SelectTrigger className="rounded-xl border-gray-200">
                                            <SelectValue placeholder="Choose a tone..." />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="urgency">Urgency — Act now</SelectItem>
                                            <SelectItem value="hope">Hope — Positive change</SelectItem>
                                            <SelectItem value="gratitude">Gratitude — Thank supporters</SelectItem>
                                            <SelectItem value="empowerment">Empowerment — You can make a difference</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Progress bar */}
                {loading && (
                    <div className="space-y-1.5 pt-2">
                        <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-moore-red rounded-full transition-all duration-500 ease-out"
                                style={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
                            />
                        </div>
                        <p className="text-xs text-moore-mid-gray text-center">
                            Step {step + 1} of {STEPS.length} — {STEPS[step]}
                        </p>
                    </div>
                )}

                <div className="flex justify-end gap-2 pt-4">
                    <button
                        type="button"
                        onClick={onClose}
                        disabled={loading}
                        className="rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm font-medium text-moore-dark-gray hover:bg-gray-50 transition-colors disabled:opacity-50"
                    >
                        Cancel
                    </button>
                    <button
                        type="submit"
                        disabled={loading}
                        className="flex items-center gap-2 rounded-xl bg-moore-red px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-moore-red-dark transition-all disabled:opacity-50"
                    >
                        {loading ? (
                            <><Loader2 className="h-4 w-4 animate-spin" /> {mode === 'custom' ? 'Creating...' : 'Generating...'}</>
                        ) : (
                            mode === 'custom' ? 'Create Campaign' : 'Generate Script'
                        )}
                    </button>
                </div>
            </form>
        </Modal>
    )
}
