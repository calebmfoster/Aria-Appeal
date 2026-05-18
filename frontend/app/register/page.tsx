"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Mail, Lock, UserPlus } from "lucide-react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function RegisterPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const router = useRouter();

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setError(null);

        if (password !== confirmPassword) {
            setError("Passwords do not match.");
            return;
        }

        if (password.length < 8) {
            setError("Password must be at least 8 characters.");
            return;
        }

        setLoading(true);

        try {
            const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password }),
            });

            if (res.ok) {
                router.push("/login?registered=true");
            } else {
                const data = await res.json();
                setError(
                    typeof data.detail === "string"
                        ? data.detail
                        : "Registration failed. Please try again."
                );
            }
        } catch {
            setError("Unable to connect to the server.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen flex-col md:flex-row bg-white text-moore-black selection:bg-moore-red/20">
            {/* Left Pane — Brand Visual */}
            <div className="relative hidden md:flex w-full md:w-1/2 overflow-hidden bg-moore-black items-center justify-center">
                <div className="absolute inset-0 z-0">
                    <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-moore-red/15 rounded-full blur-[128px]"></div>
                    <div className="absolute bottom-1/3 right-1/4 w-72 h-72 bg-moore-plum/20 rounded-full blur-[100px]"></div>
                </div>

                <div className="relative z-10 p-12 max-w-lg text-center">
                    <div className="inline-block mb-8">
                        <span className="text-5xl font-bold text-white tracking-tight">
                            <span className="text-moore-red">M</span>OORE
                        </span>
                    </div>
                    <h1 className="text-3xl lg:text-4xl font-semibold text-white mb-6 leading-tight">
                        Join Aria Appeal
                    </h1>
                    <p className="text-lg text-gray-400 font-light leading-relaxed">
                        Create your account and start crafting donor-focused audio campaigns that make a real difference.
                    </p>
                </div>
            </div>

            {/* Right Pane — Register Form */}
            <div className="flex w-full md:w-1/2 items-center justify-center p-8 lg:p-16 bg-moore-cream">
                <div className="w-full max-w-md space-y-8">
                    <div className="text-center md:text-left">
                        <h2 className="text-3xl font-semibold tracking-tight text-moore-black sm:text-4xl mb-2">
                            Create an Account
                        </h2>
                        <p className="text-sm text-moore-mid-gray">
                            Set up your credentials to get started.
                        </p>
                    </div>

                    <form onSubmit={handleSubmit} className="mt-10 space-y-6">
                        {error && (
                            <div className="p-4 rounded-xl bg-red-50 border border-moore-red/30 text-moore-red text-sm">
                                {error}
                            </div>
                        )}

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium leading-6 text-moore-dark-gray">
                                    Email address
                                </label>
                                <div className="relative mt-2">
                                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                                        <Mail className="h-5 w-5 text-moore-mid-gray" />
                                    </div>
                                    <input
                                        name="email"
                                        type="email"
                                        autoComplete="email"
                                        required
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="block w-full rounded-xl border bg-white py-3.5 pl-10 pr-4 text-moore-black shadow-sm border-gray-200 focus:ring-2 focus:ring-moore-red/30 focus:border-moore-red sm:text-sm sm:leading-6 transition-all placeholder:text-gray-400 outline-none"
                                        placeholder="you@example.com"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium leading-6 text-moore-dark-gray">
                                    Password
                                </label>
                                <div className="relative mt-2">
                                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                                        <Lock className="h-5 w-5 text-moore-mid-gray" />
                                    </div>
                                    <input
                                        name="password"
                                        type="password"
                                        autoComplete="new-password"
                                        required
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        className="block w-full rounded-xl border bg-white py-3.5 pl-10 pr-4 text-moore-black shadow-sm border-gray-200 focus:ring-2 focus:ring-moore-red/30 focus:border-moore-red sm:text-sm sm:leading-6 transition-all placeholder:text-gray-400 outline-none"
                                        placeholder="••••••••"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium leading-6 text-moore-dark-gray">
                                    Confirm Password
                                </label>
                                <div className="relative mt-2">
                                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                                        <Lock className="h-5 w-5 text-moore-mid-gray" />
                                    </div>
                                    <input
                                        name="confirmPassword"
                                        type="password"
                                        autoComplete="new-password"
                                        required
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        className="block w-full rounded-xl border bg-white py-3.5 pl-10 pr-4 text-moore-black shadow-sm border-gray-200 focus:ring-2 focus:ring-moore-red/30 focus:border-moore-red sm:text-sm sm:leading-6 transition-all placeholder:text-gray-400 outline-none"
                                        placeholder="••••••••"
                                    />
                                </div>
                            </div>
                        </div>

                        <div>
                            <button
                                type="submit"
                                disabled={loading}
                                className="flex w-full justify-center rounded-xl bg-moore-red px-3 py-3.5 text-sm font-semibold text-white shadow-sm hover:bg-moore-red-dark focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-moore-red transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <span className="flex items-center gap-2">
                                    {loading ? (
                                        <Loader2 className="h-5 w-5 animate-spin" />
                                    ) : (
                                        <>
                                            <UserPlus className="h-5 w-5" />
                                            Create Account
                                        </>
                                    )}
                                </span>
                            </button>
                        </div>
                    </form>

                    <p className="text-center text-sm text-moore-mid-gray mt-8">
                        Already have an account?{" "}
                        <Link
                            href="/login"
                            className="font-medium text-moore-red hover:text-moore-red-dark transition-colors"
                        >
                            Sign in
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
}
