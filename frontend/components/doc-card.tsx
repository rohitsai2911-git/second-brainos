import Link from "next/link";
import {
    FileText, FileCode2, Image as ImageIcon, File as FileGeneric,
    StickyNote, FileType2, Loader2, AlertCircle,
} from "lucide-react";
import type { Document } from "@/lib/types";

const TYPE_META: Record<string, { icon: typeof FileText; tint: string }> = {
    pdf: { icon: FileType2, tint: "bg-red-500/10 text-red-500" },
    code: { icon: FileCode2, tint: "bg-emerald-500/10 text-emerald-500" },
    image: { icon: ImageIcon, tint: "bg-violet-500/10 text-violet-500" },
    note: { icon: StickyNote, tint: "bg-amber-500/10 text-amber-500" },
    docx: { icon: FileText, tint: "bg-blue-500/10 text-blue-500" },
    text: { icon: FileGeneric, tint: "bg-sky-500/10 text-sky-500" },
};

export function fileTypeMeta(type: string) {
    return TYPE_META[type] || TYPE_META.text;
}

function formatSize(bytes: number) {
    if (!bytes) return "";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocCard({ doc }: { doc: Document }) {
    const meta = fileTypeMeta(doc.file_type);
    return (
        <Link
            href={`/documents/${doc.id}`}
            className="group flex flex-col rounded-xl border bg-card p-4 transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md animate-fade-in"
        >
            <div className="mb-3 flex items-start justify-between gap-2">
                <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${meta.tint}`}>
                    <meta.icon className="h-5 w-5" />
                </div>
                {doc.status !== "ready" && (
                    <span className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${
                        doc.status === "processing"
                            ? "bg-amber-500/10 text-amber-500"
                            : "bg-red-500/10 text-red-500"
                    }`}>
                        {doc.status === "processing"
                            ? <Loader2 className="h-3 w-3 animate-spin" />
                            : <AlertCircle className="h-3 w-3" />}
                        {doc.status}
                    </span>
                )}
            </div>
            <h3 className="line-clamp-1 font-semibold group-hover:text-primary">{doc.title}</h3>
            <p className="mt-1 line-clamp-2 flex-1 text-sm text-muted-foreground">
                {doc.summary || "Processing content…"}
            </p>
            {doc.tags?.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                    {doc.tags.slice(0, 3).map((t) => (
                        <span key={t} className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
                            #{t}
                        </span>
                    ))}
                </div>
            )}
            <p className="mt-3 text-xs text-muted-foreground">
                {new Date(doc.created_at).toLocaleDateString()} · {formatSize(doc.size_bytes)}
            </p>
        </Link>
    );
}
