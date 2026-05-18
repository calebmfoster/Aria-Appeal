"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, Mail, Lock } from "lucide-react";
import Link from "next/link";

export default function LoginPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const router = useRouter();
    const searchParams = useSearchParams();
    const justRegistered = searchParams.get("registered") === "true";

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        const formData = new FormData(e.currentTarget);
        const formEmail = formData.get("email") as string;
        const formPassword = formData.get("password") as string;

        const res = await signIn("credentials", {
            redirect: false,
            email: formEmail,
            password: formPassword,
        });

        if (res?.error) {
            setError("Invalid email or password.");
            setLoading(false);
        } else {
            router.push("/dashboard");
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
                        Empower Your Voice
                    </h1>
                    <p className="text-lg text-gray-400 font-light leading-relaxed">
                        Welcome back to the Aria Appeal platform. Let&apos;s continue crafting narratives that make a difference.
                    </p>
                </div>
            </div>

            {/* Right Pane — Login Form */}
            <div className="flex w-full md:w-1/2 items-center justify-center p-8 lg:p-16 bg-moore-cream">
                <div className="w-full max-w-md space-y-8">
                    <div className="text-center md:text-left">
                        <h2 className="text-3xl font-semibold tracking-tight text-moore-black sm:text-4xl mb-2">
                            Sign in to Studio
                        </h2>
                        <p className="text-sm text-moore-mid-gray">
                            Enter your credentials to access your workspace.
                        </p>
                    </div>

                    <form onSubmit={handleSubmit} className="mt-10 space-y-6">
                        {justRegistered && (
                            <div className="p-4 rounded-xl bg-green-50 border border-green-200 text-green-800 text-sm">
                                Account created successfully! Sign in to continue.
                            </div>
                        )}
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
                                        id="email"
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
                                        id="password"
                                        name="password"
                                        type="password"
                                        autoComplete="current-password"
                                        required
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
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
                                    {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : "Sign in"}
                                </span>
                            </button>
                        </div>
                    </form>

                    <p className="text-center text-sm text-moore-mid-gray mt-8">
                        Don&apos;t have an account?{" "}
                        <Link
                            href="/register"
                            className="font-medium text-moore-red hover:text-moore-red-dark transition-colors"
                        >
                            Create one
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
}
