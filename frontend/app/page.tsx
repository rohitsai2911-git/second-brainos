"use client";

import Link from "next/link";
import {
    Brain, Search, MessageSquare, Network, Layers, CalendarCheck,
    FileText, Code2, Sparkles, ArrowRight, Moon, Sun,
} from "lucide-react";
import { useTheme } from "@/components/theme-provider";
import { useAuth } from "@/lib/auth";

const features = [
    { icon: FileText, title: "Universal Ingestion", desc: "PDFs, notes, code, images, docs — everything becomes searchable knowledge." },
    { icon: Network, title: "Knowledge Graph", desc: "AI automatically connects related ideas across all your files." },
    { icon: MessageSquare, title: "RAG Chat", desc: "Ask questions and get answers grounded in your own documents with citations." },
    { icon: Search, title: "Semantic Search", desc: "Find by meaning, not keywords — powered by vector embeddings." },
    { icon: Layers, title: "Flashcards", desc: "Auto-generate flashcards and review with spaced repetition (SM-2)." },
    { icon: CalendarCheck, title: "Study Plans", desc: "AI builds day-by-day study plans from your goals and materials." },
    { icon: Code2, title: "Code Explainer", desc: "Deep, structured explanations of any code file in your knowledge base." },
    { icon: Sparkles, title: "Long-term Memory", desc: "The assistant remembers your preferences and context across sessions." },
];

export default function LandingPage() {
    const { theme, toggle } = useTheme();
    const { user } = useAuth();

    return (
        <div className="min-h-screen">
            {/* Nav */}
            <header className="sticky top-0 z-40 glass border-b">
                <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
                    <div className="flex items-center gap-2 font-semibold">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                            <Brain className="h-5 w-5" />
                        </div>
                        Second Brain OS
                    </div>
                    <div className="flex items-center gap-2">
                        <button onClick={toggle} className="rounded-lg p-2 hover:bg-muted" aria-label="Toggle theme">
                            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                        </button>
                        {user ? (
                            <Link href="/dashboard" className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90">
                                Open App
                            </Link>
                        ) : (
                            <>
                                <Link href="/auth/login" className="rounded-lg px-4 py-2 text-sm font-medium hover:bg-muted">
                                    Sign in
                                </Link>
                                <Link href="/auth/register" className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90">
                                    Get started
                                </Link>
                            </>
                        )}
                    </div>
                </div>
            </header>

            {/* Hero */}
            <section className="mx-auto max-w-6xl px-4 pb-20 pt-24 text-center">
                <div className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border bg-card px-4 py-1.5 text-sm text-muted-foreground">
                    <Sparkles className="h-4 w-4 text-primary" />
                    Your personal AI knowledge operating system
                </div>
                <h1 className="mx-auto max-w-3xl text-5xl font-bold leading-tight tracking-tight md:text-6xl">
                    Never forget <span className="gradient-text">anything</span> you learn
                </h1>
                <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
                    Upload your documents, notes, and code. Second Brain OS organizes everything into a
                    living knowledge graph, answers questions with citations, generates flashcards,
                    and plans your learning — automatically.
                </p>
                <div className="mt-10 flex items-center justify-center gap-4">
                    <Link
                        href={user ? "/dashboard" : "/auth/register"}
                        className="inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3 font-medium text-primary-foreground shadow-lg shadow-primary/25 hover:opacity-90"
                    >
                        Start building your brain <ArrowRight className="h-4 w-4" />
                    </Link>
                    <Link href="/auth/login" className="rounded-xl border bg-card px-6 py-3 font-medium hover:bg-muted">
                        Sign in
                    </Link>
                </div>
            </section>

            {/* Features */}
            <section className="mx-auto max-w-6xl px-4 pb-24">
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    {features.map((f) => (
                        <div key={f.title} className="rounded-xl border bg-card p-5 transition-shadow hover:shadow-lg">
                            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                                <f.icon className="h-5 w-5" />
                            </div>
                            <h3 className="font-semibold">{f.title}</h3>
                            <p className="mt-1 text-sm text-muted-foreground">{f.desc}</p>
                        </div>
                    ))}
                </div>
            </section>

            <footer className="border-t py-8 text-center text-sm text-muted-foreground">
                Second Brain OS — Next.js · FastAPI · PostgreSQL · Qdrant
            </footer>
        </div>
    );
}
