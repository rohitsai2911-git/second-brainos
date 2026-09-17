"use client";

import { useCallback, useEffect, useRef, useState } from "react";
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
    const [loadError, setLoadError] = useState("");
    const [noteError, setNoteError] = useState("");
    const [failedFiles, setFailedFiles] = useState<File[]>([]);
    const [uploadProgress, setUploadProgress] = useState({ completed: 0, total: 0 });
    const busyRef = useRef(false);
    const refreshVersion = useRef(0);

    const refresh = useCallback(async () => {
        const version = ++refreshVersion.current;
        try {
            const documents = await api.get<Document[]>("/api/documents");
            if (version !== refreshVersion.current) return;
            setDocs(documents);
            setLoadError("");
        } catch {
            if (version === refreshVersion.current) {
                setLoadError("Could not load documents. Please try again.");
            }
        } finally {
            if (version === refreshVersion.current) setLoading(false);
        }
    }, []);

    useEffect(() => { void refresh(); }, [refresh]);

    const processing = docs.some((d) => d.status === "processing");
    useEffect(() => {
        if (!processing) return;
        const t = setInterval(() => { void refresh(); }, 2500);
        return () => clearInterval(t);
    }, [processing, refresh]);

    const uploadFiles = async (files: File[]) => {
        if (files.length === 0 || busyRef.current) return;
        busyRef.current = true;
        setBusy(true);
        setUploadProgress({ completed: 0, total: files.length });
        setFailedFiles((previous) => previous.filter((file) => !files.includes(file)));
        try {
            for (const file of files) {
                try {
                    const form = new FormData();
                    form.append("file", file);
                    const uploaded = await api.upload<Document>("/api/documents/upload", form);
                    setDocs((previous) => [uploaded, ...previous.filter((d) => d.id !== uploaded.id)]);
                    void refresh();
                } catch {
                    setFailedFiles((previous) => [...previous, file]);
                } finally {
                    setUploadProgress((previous) => ({ ...previous, completed: previous.completed + 1 }));
                }
            }
        } finally {
            busyRef.current = false;
            setBusy(false);
        }
    };

    const saveNote = async () => {
        if (!noteTitle.trim() || busyRef.current) return;
        busyRef.current = true;
        setBusy(true);
        setNoteError("");
        setUploadProgress({ completed: 0, total: 0 });
        try {
            const note = await api.post<Document>("/api/documents/notes", { title: noteTitle.trim(), content: noteBody });
            setDocs((previous) => [note, ...previous.filter((d) => d.id !== note.id)]);
            setNoteOpen(false);
            setNoteTitle("");
            setNoteBody("");
            void refresh();
        } catch {
            setNoteError("Could not save note. Your text is still here; please try again.");
        } finally {
            busyRef.current = false;
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
                    {noteError && <p role="alert" className="text-sm text-red-500">{noteError}</p>}
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
            {(busy || uploadProgress.total > 0) && (
                <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
                    {busy && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
                    {uploadProgress.total > 0
                        ? `${uploadProgress.completed} of ${uploadProgress.total} upload attempts completed${busy ? "…" : "."}`
                        : "Saving note…"}
                </p>
            )}
            {failedFiles.length > 0 && (
                <div className="space-y-2 rounded-xl border bg-card p-4">
                    <ul role="alert" className="space-y-1 text-sm text-red-500">
                        {failedFiles.map((file, index) => (
                            <li key={index} className="break-words">{file.name}: Upload failed. Please retry.</li>
                        ))}
                    </ul>
                    <button
                        onClick={() => uploadFiles(failedFiles)}
                        disabled={busy}
                        className="rounded-lg border px-3.5 py-2 text-sm font-medium hover:bg-muted disabled:opacity-40"
                    >
                        Retry failed uploads ({failedFiles.length})
                    </button>
                </div>
            )}
            {loadError && (
                <div role="alert" className="flex items-center gap-3 text-sm text-red-500">
                    <p>{loadError}</p>
                    <button onClick={() => { void refresh(); }} className="text-primary hover:underline">Reload</button>
                </div>
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
