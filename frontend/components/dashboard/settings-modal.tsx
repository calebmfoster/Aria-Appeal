"use client"
import * as React from "react"
import { Modal } from "@/components/ui/modal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { API_URL } from "@/lib/config"
import toast from 'react-hot-toast'

interface SettingsModalProps {
    isOpen: boolean
    onClose: () => void
}

interface SystemSettings {
    llm_provider: "ollama" | "openai"
    llm_base_url: string
    llm_api_key: string
    llm_model: string
    tts_provider: "qwen3-local" | "openai"
    tts_model: string
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
    const [loading, setLoading] = React.useState(false)
    const [activeTab, setActiveTab] = React.useState<"copy" | "audio">("copy")
    const [settings, setSettings] = React.useState<SystemSettings>({
        llm_provider: "ollama",
        llm_base_url: "http://localhost:11434/v1",
        llm_api_key: "ollama",
        llm_model: "llama3",
        tts_provider: "qwen3-local",
        tts_model: "qwen3-tts",
    })

    // Fetch settings on open
    React.useEffect(() => {
        if (isOpen) {
            fetch(`${API_URL}/settings`)
                .then((res) => res.json())
                .then((data) => setSettings(data))
                .catch((err) => console.error("Failed to load settings:", err))
        }
    }, [isOpen])

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        setSettings({ ...settings, [e.target.name]: e.target.value })
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)
        try {
            const res = await fetch(`${API_URL}/settings`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(settings),
            })
            if (!res.ok) throw new Error("Failed to save settings")
            toast.success("Settings saved successfully")
            onClose()
        } catch (error) {
            console.error(error)
            toast.error("Error saving settings.")
        } finally {
            setLoading(false)
        }
    }

    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Settings" className="max-w-2xl">
            <div className="flex border-b mb-4">
                <button
                    className={`px-4 py-2 font-medium text-sm ${activeTab === "copy" ? "border-b-2 border-primary" : "text-muted-foreground"}`}
                    onClick={() => setActiveTab("copy")}
                >
                    Copywriting (LLM)
                </button>
                <button
                    className={`px-4 py-2 font-medium text-sm ${activeTab === "audio" ? "border-b-2 border-primary" : "text-muted-foreground"}`}
                    onClick={() => setActiveTab("audio")}
                >
                    Audio Generation (TTS)
                </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
                {activeTab === "copy" && (
                    <div className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Provider</label>
                            <select
                                name="llm_provider"
                                value={settings.llm_provider}
                                onChange={handleChange}
                                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                            >
                                <option value="ollama">Ollama (Local)</option>
                                <option value="openai">OpenAI</option>
                            </select>
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Base URL</label>
                            <Input name="llm_base_url" value={settings.llm_base_url} onChange={handleChange} />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">API Key</label>
                            <Input name="llm_api_key" type="password" value={settings.llm_api_key} onChange={handleChange} />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Model Name</label>
                            <Input name="llm_model" value={settings.llm_model} onChange={handleChange} />
                        </div>
                    </div>
                )}

                {activeTab === "audio" && (
                    <div className="space-y-4">
                        <div className="p-4 bg-muted rounded-md text-sm text-muted-foreground">
                            TTS Settings are currently placeholders for Phase III implementation.
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Provider</label>
                            <select
                                name="tts_provider"
                                value={settings.tts_provider}
                                onChange={handleChange}
                                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                            >
                                <option value="qwen3-local">Qwen3-TTS (Local)</option>
                                <option value="openai">OpenAI TTS</option>
                            </select>
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Model Name</label>
                            <Input name="tts_model" value={settings.tts_model} onChange={handleChange} />
                        </div>
                    </div>
                )}

                <div className="flex justify-end space-x-2 pt-4 border-t mt-6">
                    <Button variant="outline" type="button" onClick={onClose} disabled={loading}>Cancel</Button>
                    <Button type="submit" disabled={loading}>{loading ? "Saving..." : "Save Settings"}</Button>
                </div>
            </form>
        </Modal>
    )
}
