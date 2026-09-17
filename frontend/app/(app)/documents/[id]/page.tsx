"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import {
    ArrowLeft, Layers, Download, Trash2, Loader2, Code2,
    FileText, Sparkles, Network,
} from "lucide-react";
import { api } from "@/lib/api";
import type { DocumentDetail } from "@/lib/types";
import { fileTypeMeta } from "@/components/doc-card";

export default function DocumentViewerPage() {
    const { id } = useParams<{ id: string }>();
    const router = useRouter();
    const [doc, setDoc] = useState<DocumentDetail | null>(null);
    const [error, setError] = useState("");
    const [explanation, setExplanation] = useState("");
    const [actionBusy, setActionBusy] = useState("");

    const load = useCallback(() => {
        api.get<DocumentDetail>(`/api/documents/${id}`).then(setDoc).catch((e) => setError(e.message));
    }, [id]);

    useEffect(load, [load]);

    useEffect(() => {
        if (doc?.status === "processing") {
            const t = setTimeout(load, 2000);
            return () => clearTimeout(t);
        }
    }, [doc, load]);

    const generateFlashcards = async () => {
        setActionBusy("flashcards");
        try {
            await api.post("/api/flashcards/generate", { document_id: id, count: 10 });
            router.push("/flashcards");
        } catch (e) {
            alert(e instanceof Error ? e.message : "Generation failed");
        } finally {
            setActionBusy("");
        }
    };

    const explainCode = async () => {
        setActionBusy("explain");
        setExplanation("");
        try {
            const res = await api.post<{ explanation: string }>(`/api/documents/${id}/explain`);
            setExplanation(res.explanation);
        } catch (e) {
            alert(e instanceof Error ? e.message : "Explanation failed");
        } finally {
            setActionBusy("");
        }
    };

    const deleteDoc = async () => {
        if (!confirm(`Delete "${doc?.title}"? This removes its chunks and graph links.`)) return;
        await api.delete(`/api/documents/${id}`);
        router.push("/documents");
    };

    if (error) {
        return (
            <div className="space-y-4">
                <p className="text-sm text-red-500">{error}</p>
                <Link href="/documents" className="text-sm text-primary hover:underline">← Back to documents</Link>
            </div>
        );
    }
    if (!doc) {
        return (
            <div className="flex h-64 items-center justify-center">
                <Loader2 className="h-7 w-7 animate-spin text-primary" />
            </div>
        );
    }

    const meta = fileTypeMeta(doc.file_type);

    return (
        <div className="mx-auto max-w-4xl space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <Link href="/documents" className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-primary">
                    <ArrowLeft className="h-4 w-4" /> Documents
                </Link>
                <div className="flex gap-2">
                    {doc.file_type !== "note" && (
                        <a
                            href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/documents/${doc.id}/file`}
                            target="_blank"
                            rel="noreferrer"
                            className="flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium hover:bg-muted"
                        >
                            <Download className="h-4 w-4" /> Original
                        </a>
                    )}
                    <button onClick={deleteDoc} aria-label="Delete document"
                        className="flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium hover:bg-muted hover:text-red-500">
                        <Trash2 className="h-4 w-4" /> Delete
                    </button>
                </div>
            </div>

            <header className="flex items-start gap-4">
                <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${meta.tint}`}>
                    <meta.icon className="h-6 w-6" />
                </div>
                <div className="min-w-0">
                    <h1 className="text-2xl font-bold">{doc.title}</h1>
                    <p className="text-sm text-muted-foreground">
                        {doc.filename} · {new Date(doc.created_at).toLocaleDateString()} ·{" "}
                        {(doc.size_bytes / 1024).toFixed(1)} KB ·{" "}
                        <span className={doc.status === "ready" ? "text-emerald-500" : "text-amber-500"}>{doc.status}</span>
                    </p>
                    {doc.tags?.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                            {doc.tags.map((t) => (
                                <span key={t} className="rounded-full bg-muted px-2.5 py-0.5 text-xs text-muted-foreground">#{t}</span>
                            ))}
                        </div>
                    )}
                </div>
            </header>

            {doc.status === "processing" && (
                <div className="flex items-center gap-3 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-sm">
                    <Loader2 className="h-4 w-4 animate-spin text-amber-500" />
                    AI is summarizing, tagging and indexing this document…
                </div>
            )}

            {doc.summary && (
                <section className="rounded-xl border bg-card p-5">
                    <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-muted-foreground">
                        <Sparkles className="h-4 w-4 text-primary" /> AI SUMMARY
                    </h2>
                    <p className="prose-sbo text-sm">{doc.summary}</p>
                </section>
            )}

            <section className="flex flex-wrap gap-2">
                <button
                    onClick={generateFlashcards}
                    disabled={actionBusy !== "" || doc.status !== "ready"}
                    className="flex items-center gap-2 rounded-lg bg-primary px-3.5 py-2 text-sm font-medium text-primary-foreground disabled:opacity-40"
                >
                    {actionBusy === "flashcards" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Layers className="h-4 w-4" />}
                    Generate flashcards
                </button>
                <Link
                    href={`/search`}
                    className="flex items-center gap-2 rounded-lg border px-3.5 py-2 text-sm font-medium hover:bg-muted"
                >
                    <Network className="h-4 w-4" /> Find related
                </Link>
                <button
                    onClick={explainCode}
                    disabled={actionBusy !== ""}
                    className="flex items-center gap-2 rounded-lg border px-3.5 py-2 text-sm font-medium hover:bg-muted disabled:opacity-40"
                >
                    {actionBusy === "explain" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Code2 className="h-4 w-4" />}
                    Explain this content
                </button>
            </section>

            {explanation && (
                <section className="rounded-xl border bg-card p-5">
                    <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-muted-foreground">
                        <Code2 className="h-4 w-4 text-accent" /> AI EXPLANATION
                    </h2>
                    <div className="prose-sbo text-sm"><ReactMarkdown>{explanation}</ReactMarkdown></div>
                </section>
            )}

            <section className="rounded-xl border bg-card p-5">
                <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-muted-foreground">
                    <FileText className="h-4 w-4" /> EXTRACTED CONTENT
                </h2>
                <pre className="max-h-[28rem] overflow-y-auto whitespace-pre-wrap break-words font-sans text-sm leading-relaxed">
                    {doc.content_text || "(no extractable text)"}
                </pre>
            </section>
        </div>
    );
}
