"use client";

import { useState } from "react";
import Link from "next/link";
import { Brain, Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
    const { login } = useAuth();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            await login(email, password);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Login failed");
            setLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center px-4">
            <div className="w-full max-w-sm animate-fade-in">
                <div className="mb-8 text-center">
                    <Link href="/" className="inline-flex items-center gap-2 font-semibold">
                        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                            <Brain className="h-5 w-5" />
                        </div>
                        Second Brain OS
                    </Link>
                    <h1 className="mt-6 text-2xl font-bold">Welcome back</h1>
                    <p className="mt-1 text-sm text-muted-foreground">Sign in to your knowledge base</p>
                </div>

                <form onSubmit={submit} className="space-y-4 rounded-xl border bg-card p-6">
                    {error && (
                        <div className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-500">{error}</div>
                    )}
                    <div>
                        <label className="mb-1.5 block text-sm font-medium">Email</label>
                        <input
                            type="email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/50"
                            placeholder="you@example.com"
                        />
                    </div>
                    <div>
                        <label className="mb-1.5 block text-sm font-medium">Password</label>
                        <input
                            type="password"
                            required
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/50"
                            placeholder="••••••••"
                        />
                    </div>
                    <button
                        type="submit"
                        disabled={loading}
                        className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-60"
                    >
                        {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                        Sign in
                    </button>
                </form>

                <p className="mt-4 text-center text-sm text-muted-foreground">
                    No account?{" "}
                    <Link href="/auth/register" className="font-medium text-primary hover:underline">
                        Create one
                    </Link>
                </p>
            </div>
        </div>
    );
}
