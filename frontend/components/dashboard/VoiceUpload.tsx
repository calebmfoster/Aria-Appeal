'use client';

import React, { useState, useRef } from 'react';
import { Input } from '@/components/ui/input';
import { API_URL } from '@/lib/config';
import { useSession } from 'next-auth/react';
import { Upload, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

interface VoiceUploadProps {
    onUploadSuccess?: () => void;
}

interface ValidationResult {
    is_valid: boolean;
    lufs: number;
    speech_ratio: number;
    errors: string[];
}

export const VoiceUpload: React.FC<VoiceUploadProps> = ({ onUploadSuccess }) => {
    const [name, setName] = useState('');
    const [referenceText, setReferenceText] = useState('');
    const [file, setFile] = useState<File | null>(null);
    const [isUploading, setIsUploading] = useState(false);
    const [isValidating, setIsValidating] = useState(false);
    const [validation, setValidation] = useState<ValidationResult | null>(null);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const { data: session } = useSession();

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        if (selectedFile) {
            setFile(selectedFile);
            setIsValidating(true);
            setValidation(null);
            await validateAudio(selectedFile);
            setIsValidating(false);
        }
    };

    const validateAudio = async (selectedFile: File) => {
        const formData = new FormData();
        formData.append('file', selectedFile);

        try {
            const response = await fetch(`${API_URL}/voice-profiles/validate`, {
                method: 'POST',
                body: formData,
            });

            if (response.ok) {
                const data = await response.json();
                setValidation(data);
            }
        } catch (error) {
            console.error('Validation error:', error);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!file || !name) return;

        setIsUploading(true);
        setMessage(null);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('name', name);
        formData.append('base_model', 'Qwen3-TTS-12Hz-1.7B-Base');
        if (referenceText.trim()) {
            formData.append('reference_text', referenceText.trim());
        }

        try {
            const response = await fetch(`${API_URL}/voice-profiles/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${session?.accessToken}`
                },
                body: formData,
            });

            if (response.ok) {
                setMessage({ type: 'success', text: 'Voice profile created successfully!' });
                setName('');
                setReferenceText('');
                setFile(null);
                setValidation(null);
                if (fileInputRef.current) fileInputRef.current.value = '';
                onUploadSuccess?.();
            } else {
                const errorData = await response.json();
                let errMsg = 'Failed to upload voice profile.';
                if (typeof errorData.detail === 'string') {
                    errMsg = errorData.detail;
                } else if (errorData.detail?.message) {
                    errMsg = errorData.detail.message;
                }

                if (response.status === 401 || response.status === 403) {
                    errMsg = 'Your session has expired. Please refresh the page or log out and log back in.';
                }

                setMessage({ type: 'error', text: errMsg });
            }
        } catch (error) {
            setMessage({ type: 'error', text: 'An unexpected error occurred.' });
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm space-y-5">
            <h2 className="text-lg font-semibold text-moore-black tracking-tight">
                Add Voice Profile
            </h2>

            <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-1.5">
                    <label className="text-sm font-medium text-moore-dark-gray">Profile Name</label>
                    <Input
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="e.g. Professional Male 1"
                        className="rounded-xl border-gray-200 bg-white text-moore-black focus:ring-2 focus:ring-moore-red/30 focus:border-moore-red"
                        required
                    />
                </div>

                <div className="space-y-1.5">
                    <label className="text-sm font-medium text-moore-dark-gray">
                        Reference Transcript <span className="text-moore-mid-gray">(optional)</span>
                    </label>
                    <textarea
                        value={referenceText}
                        onChange={(e) => setReferenceText(e.target.value)}
                        placeholder="Type or paste the exact words spoken in your audio sample."
                        className="w-full rounded-xl border border-gray-200 bg-white text-moore-black px-3 py-2 text-sm focus:ring-2 focus:ring-moore-red/30 focus:border-moore-red resize-none outline-none transition-all placeholder:text-gray-400"
                        rows={3}
                    />
                </div>

                <div className="space-y-1.5">
                    <label className="text-sm font-medium text-moore-dark-gray">Voice Sample (WAV/MP3)</label>
                    <label className="flex flex-col items-center justify-center w-full h-28 border-2 border-gray-200 border-dashed rounded-xl cursor-pointer bg-moore-cream/50 hover:bg-moore-cream transition-colors">
                        <div className="flex flex-col items-center justify-center py-4">
                            {isValidating ? (
                                <Loader2 className="w-6 h-6 text-moore-mid-gray animate-spin mb-2" />
                            ) : (
                                <Upload className="w-6 h-6 text-moore-mid-gray mb-2" />
                            )}
                            <p className="text-sm text-moore-mid-gray">
                                {isValidating ? 'Validating...' : file ? file.name : 'Click to upload'}
                            </p>
                            {!file && <p className="text-xs text-gray-400">Audio file (max 10MB)</p>}
                        </div>
                        <input
                            ref={fileInputRef}
                            type="file"
                            className="hidden"
                            onChange={handleFileChange}
                            accept="audio/*"
                            required
                        />
                    </label>
                </div>

                {validation && (
                    <div className={`p-3 rounded-xl border text-sm ${validation.is_valid
                        ? 'bg-green-50 border-green-200'
                        : 'bg-red-50 border-red-200'
                    }`}>
                        <div className={`flex items-center gap-2 font-medium ${validation.is_valid ? 'text-green-700' : 'text-red-700'}`}>
                            {validation.is_valid ? (
                                <><CheckCircle2 className="w-4 h-4" /> Quality: Passed</>
                            ) : (
                                <><AlertCircle className="w-4 h-4" /> Quality: Needs Improvement</>
                            )}
                        </div>
                        <div className="mt-1.5 space-y-0.5 text-xs text-moore-mid-gray">
                            <p>Loudness: <span className="text-moore-dark-gray font-medium">{validation.lufs.toFixed(2)} LUFS</span></p>
                            <p>Speech Clarity: <span className="text-moore-dark-gray font-medium">{(validation.speech_ratio * 100).toFixed(1)}%</span></p>
                            {validation.errors.length > 0 && (
                                <ul className="mt-1.5 space-y-0.5 text-red-600">
                                    {validation.errors.map((err, i) => <li key={i}>• {err}</li>)}
                                </ul>
                            )}
                        </div>
                    </div>
                )}

                <button
                    type="submit"
                    disabled={isUploading || !file || !name || (validation?.is_valid === false)}
                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-moore-red px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-moore-red-dark transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {isUploading ? (
                        <><Loader2 className="h-4 w-4 animate-spin" /> Uploading...</>
                    ) : (
                        'Save Voice Profile'
                    )}
                </button>

                {message && (
                    <p className={`text-center text-sm font-medium ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                        {message.text}
                    </p>
                )}
            </form>
        </div>
    );
};
