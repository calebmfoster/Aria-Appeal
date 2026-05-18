import * as React from "react"
import { X } from "lucide-react"

interface ModalProps {
    isOpen: boolean
    onClose: () => void
    title: string
    children: React.ReactNode
    className?: string
}

export function Modal({ isOpen, onClose, title, children, className }: ModalProps) {
    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
            <div className={`relative w-full max-w-lg rounded-2xl border border-gray-200 bg-white p-6 shadow-xl ${className || ''}`}>
                <div className="flex items-center justify-between mb-5">
                    <h2 className="text-lg font-semibold text-moore-black tracking-tight">{title}</h2>
                    <button
                        onClick={onClose}
                        className="h-8 w-8 rounded-full flex items-center justify-center text-moore-mid-gray hover:text-moore-black hover:bg-gray-100 transition-colors"
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>
                {children}
            </div>
        </div>
    )
}
