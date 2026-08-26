"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
    FileText, MessageSquare, Layers, CalendarCheck, Network,
    Brain, Upload, Sparkles, Loader2, Tag,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Stats } from "@/lib/types";
import StatCard from "@/components/stat-card";
import DocCard from "@/components/doc-card";

export default function DashboardPage() {
    const [stats, setStats] = useState<Stats | null>(null);
    const [error, setError] = useState("");

    useEffect(() => {
        api.get<Stats>("/api/stats").then(setStats).catch((e) => setError(e.message));
    }, []);

    if (error) return <p className="text-sm text-red-500">{error}</p>;
    if (!stats) {
        return (
            <div className="flex h-64 items-center justify-center">
                <Loader2 className="h-7 w-7 animate-spin text-primary" />
            </div>
        );
    }

    const kbSize = stats.total_size_bytes > 1024 * 1024
        ? `${(stats.total_size_bytes / 1024 / 1024).toFixed(1)} MB`
        : `${(stats.total_size_bytes / 1024).toFixed(0)} KB`;

    return (
        <div className="space-y-8">
            <header className="flex flex-wrap items-end justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold">Dashboard</h1>
                    <p className="text-sm text-muted-foreground">Your knowledge base at a glance</p>
                </div>
                <div className="flex gap-2">
                    <Link href="/documents" className="flex items-center gap-2 rounded-lg border px-3.5 py-2 text-sm font-medium hover:bg-muted">
                        <Upload className="h-4 w-4" /> Upload
                    </Link>
                    <Link href="/chat" className="flex items-center gap-2 rounded-lg bg-primary px-3.5 py-2 text-sm font-medium text-primary-foreground hover:opacity-90">
                        <MessageSquare className="h-4 w-4" /> Ask AI
                    </Link>
                </div>
            </header>

            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                <StatCard icon={FileText} label="Documents" value={stats.total_documents}
                    sub={`${kbSize} · ${stats.total_chunks} chunks indexed`} href="/documents" />
                <StatCard icon={Layers} label="Flashcards" value={stats.total_flashcards}
                    sub={`${stats.due_flashcards} due for review`} href="/flashcards" />
                <StatCard icon={CalendarCheck} label="Tasks" value={stats.total_tasks}
                    sub={`${stats.completed_tasks} completed`} href="/planner" />
                <StatCard icon={Network} label="Connections" value={stats.total_links}
                    sub="semantic links in your graph" href="/graph" />
                <StatCard icon={Brain} label="Memories" value={stats.total_memories}
                    sub="facts the AI remembers about you" href="/chat" />
                <StatCard icon={Sparkles} label="Top topics" value={stats.top_tags.length}
                    sub={stats.top_tags.slice(0, 3).join(", ") || "no tags yet"} />
            </section>

            {stats.top_tags.length > 0 && (
                <section>
                    <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-muted-foreground">
                        <Tag className="h-4 w-4" /> KNOWLEDGE MAP
                    </h2>
                    <div className="flex flex-wrap gap-2">
                        {stats.top_tags.map((t, i) => (
                            <Link key={t} href={`/search`}
                                className="rounded-full border bg-card px-3 py-1.5 text-sm transition-colors hover:border-primary/50 hover:text-primary"
                                style={{ opacity: 1 - i * 0.07 }}>
                                #{t}
                            </Link>
                        ))}
                    </div>
                </section>
            )}

            <section>
                <div className="mb-3 flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-muted-foreground">RECENT DOCUMENTS</h2>
                    <Link href="/documents" className="text-sm font-medium text-primary hover:underline">View all</Link>
                </div>
                {stats.recent_documents.length === 0 ? (
                    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed py-14 text-center">
                        <Upload className="h-8 w-8 text-muted-foreground" />
                        <p className="font-medium">Your second brain is empty</p>
                        <p className="max-w-xs text-sm text-muted-foreground">
                            Upload PDFs, notes or code and the AI will organize everything automatically.
                        </p>
                        <Link href="/documents" className="mt-1 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
                            Upload your first document
                        </Link>
                    </div>
                ) : (
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
                        {stats.recent_documents.map((d) => <DocCard key={d.id} doc={d} />)}
                    </div>
                )}
            </section>
        </div>
    );
}
