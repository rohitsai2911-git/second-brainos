"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Plus, StickyNote, Search as SearchIcon } from "lucide-react";
import { api } from "@/lib/api";
import type { Document } from "@/lib/types";
import DocCard, { fileTypeMeta } from "@/components/doc-card";
import UploadZone from "@/components/upload-zone";

const FILTERS = ["all", "pdf", "note", "code", "image", "docx", "text"];

export default function DocumentsPage() {
    const [docs, setDocs] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState("all");
    const [query, setQuery] = useState("");
    const [noteOpen, setNoteOpen] = useState(false);
    const [noteTitle, setNoteTitle] = useState("");
    const [noteBody, setNoteBody] = useState("");
    const [busy, setBusy] = useState(false);

    const refresh = useCallback(() => {
        api.get<Document[]>("/api/documents").then(setDocs).finally(() => setLoading(false));
    }, []);

    useEffect(refresh, [refresh]);

    useEffect(() => {
        if (docs.some((d) => d.status === "processing")) {
            const t = setTimeout(refresh, 2500);
            return () => clearTimeout(t);
        }
    }, [docs, refresh]);

    const uploadFiles = async (files: File[]) => {
        if (files.length === 0) return;
        setBusy(true);
        try {
            for (const f of files) {
                const form = new FormData();
                form.append("file", f);
                await api.upload("/api/documents/upload", form);
            }
            refresh();
        } finally {
            setBusy(false);
        }
    };

    const saveNote = async () => {
        if (!noteTitle.trim() || busy) return;
        setBusy(true);
        try {
            await api.post("/api/documents/notes", { title: noteTitle.trim(), content: noteBody });
            setNoteOpen(false);
            setNoteTitle("");
            setNoteBody("");
            refresh();
        } finally {
            setBusy(false);
        }
    };

    const visible = docs.filter((d) =>
        (filter === "all" || d.file_type === filter) &&
        (!query ||
            d.title.toLowerCase().includes(query.toLowerCase()) ||
            d.tags?.some((t) => t.includes(query.toLowerCase())))
    );

    return (
        <div className="space-y-6">
            <header className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h1 className="text-2xl font-bold">Documents</h1>
                    <p className="text-sm text-muted-foreground">Everything you know, in one place</p>
                </div>
                <button
                    onClick={() => setNoteOpen(!noteOpen)}
                    className="flex items-center gap-2 rounded-lg border px-3.5 py-2 text-sm font-medium hover:bg-muted"
                >
                    <Plus className="h-4 w-4" /> New note
                </button>
            </header>

            {noteOpen && (
                <div className="space-y-3 rounded-xl border bg-card p-4 animate-fade-in">
                    <input
                        autoFocus
                        value={noteTitle}
                        onChange={(e) => setNoteTitle(e.target.value)}
                        placeholder="Note title"
                        className="w-full rounded-lg border bg-background px-3 py-2 text-sm font-medium outline-none focus:border-primary"
                    />
                    <textarea
                        value={noteBody}
                        onChange={(e) => setNoteBody(e.target.value)}
                        rows={5}
                        placeholder="Write anything — the AI will summarize, tag and index it automatically."
                        className="w-full resize-y rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                    />
                    <button
                        onClick={saveNote}
                        disabled={!noteTitle.trim() || busy}
                        className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-40"
                    >
                        Save note
                    </button>
                </div>
            )}

            <UploadZone onFiles={uploadFiles} disabled={busy} />
            {busy && (
                <p className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin text-primary" /> Uploading and processing…
                </p>
            )}

            <div className="flex flex-wrap items-center gap-2">
                <div className="relative mr-auto w-full max-w-xs">
                    <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <input
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Filter by title or #tag"
                        className="w-full rounded-lg border bg-card py-2 pl-9 pr-3 text-sm outline-none focus:border-primary"
                    />
                </div>
                {FILTERS.map((f) => {
                    const meta = fileTypeMeta(f);
                    return (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={`rounded-lg px-3 py-1.5 text-sm font-medium capitalize transition-colors ${
                                filter === f ? "bg-primary text-primary-foreground" : "border hover:bg-muted"
                            }`}
                        >
                            {f === "all" ? "All" : f === "text" ? "Text" : f}
                            {f !== "all" && f !== "text" && <meta.icon className="ml-1 inline h-3.5 w-3.5" />}
                            {f === "note" && <StickyNote className="ml-1 inline h-3.5 w-3.5" />}
                        </button>
                    );
                })}
            </div>

            {loading ? (
                <div className="flex h-48 items-center justify-center">
                    <Loader2 className="h-7 w-7 animate-spin text-primary" />
                </div>
            ) : visible.length === 0 ? (
                <p className="py-16 text-center text-sm text-muted-foreground">No documents match.</p>
            ) : (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {visible.map((d) => <DocCard key={d.id} doc={d} />)}
                </div>
            )}
        </div>
    );
}
