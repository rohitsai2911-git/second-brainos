"use client";

import { useState } from "react";
import Link from "next/link";
import { Search as SearchIcon, Loader2, FileText } from "lucide-react";
import { api } from "@/lib/api";
import type { SearchResult } from "@/lib/types";
import { fileTypeMeta } from "@/components/doc-card";

export default function SearchPage() {
    const [query, setQuery] = useState("");
    const [results, setResults] = useState<SearchResult[] | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const search = async (q: string) => {
        if (!q.trim()) return;
        setLoading(true);
        setError("");
        try {
            setResults(await api.post<SearchResult[]>("/api/search", { query: q.trim(), limit: 20 }));
        } catch (e) {
            setError(e instanceof Error ? e.message : "Search failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="mx-auto max-w-3xl space-y-6">
            <header>
                <h1 className="text-2xl font-bold">Semantic Search</h1>
                <p className="text-sm text-muted-foreground">Find by meaning, not keywords — powered by vector embeddings</p>
            </header>

            <div className="relative">
                <SearchIcon className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
                <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && search(query)}
                    autoFocus
                    placeholder="e.g. how do attention mechanisms work?"
                    className="w-full rounded-xl border bg-card py-3.5 pl-12 pr-24 text-sm shadow-sm outline-none focus:border-primary"
                />
                <button
                    onClick={() => search(query)}
                    disabled={loading || !query.trim()}
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-40"
                >
                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Search"}
                </button>
            </div>

            {error && <p className="text-sm text-red-500">{error}</p>}

            {results !== null && results.length === 0 && !loading && (
                <p className="py-14 text-center text-sm text-muted-foreground">
                    Nothing found. Try different phrasing or upload more material.
                </p>
            )}

            <div className="space-y-3">
                {results?.map((r, i) => {
                    const meta = fileTypeMeta(r.file_type);
                    return (
                        <Link
                            key={`${r.chunk_id}-${i}`}
                            href={`/documents/${r.document_id}`}
                            className="block rounded-xl border bg-card p-4 transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md animate-fade-in"
                            style={{ animationDelay: `${i * 30}ms` }}
                        >
                            <div className="mb-2 flex items-center justify-between gap-3">
                                <span className="flex min-w-0 items-center gap-2 text-sm font-semibold">
                                    <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-md ${meta.tint}`}>
                                        <meta.icon className="h-3.5 w-3.5" />
                                    </span>
                                    <span className="truncate">{r.document_title}</span>
                                </span>
                                <span className="shrink-0 text-xs font-medium text-primary">
                                    {(r.score * 100).toFixed(0)}% match
                                </span>
                            </div>
                            <div className="mb-2.5 h-1 overflow-hidden rounded-full bg-muted">
                                <div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(r.score * 100, 100)}%` }} />
                            </div>
                            <p className="line-clamp-3 text-sm leading-relaxed text-muted-foreground">{r.text}</p>
                        </Link>
                    );
                })}
            </div>

            {results === null && !loading && (
                <div className="flex flex-col items-center gap-2 py-16 text-center text-muted-foreground">
                    <FileText className="h-8 w-8" />
                    <p className="text-sm">Search across every document you've uploaded.</p>
                </div>
            )}
        </div>
    );
}
