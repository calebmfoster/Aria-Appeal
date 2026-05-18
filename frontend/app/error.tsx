'use client' // Error boundaries must be Client Components

import { useEffect } from 'react'

export default function ErrorBoundary({
    error,
    reset,
}: {
    error: Error & { digest?: string }
    reset: () => void
}) {
    useEffect(() => {
        // Log the error to an error reporting service
        console.error("Global Error Boundary caught an error:", error)
    }, [error])

    return (
        <div className="flex flex-col items-center justify-center min-h-screen p-4 bg-background text-foreground">
            <div className="bg-card border rounded-lg shadow-sm p-8 max-w-md w-full text-center">
                <h2 className="text-2xl font-bold mb-4">Something went wrong!</h2>
                <p className="text-muted-foreground mb-6">
                    An unexpected error occurred in the application. We've been notified and are looking into it.
                </p>
                <button
                    className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
                    onClick={() => reset()}
                >
                    Try again
                </button>
            </div>
        </div>
    )
}
