"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, Network, ArrowUpRight, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import type { Graph as GraphData, GraphNode } from "@/lib/types";
import GraphCanvas from "@/components/graph-canvas";

const LEGEND = [
    { type: "pdf", color: "#ef4444" },
    { type: "code", color: "#10b981" },
    { type: "image", color: "#8b5cf6" },
    { type: "note", color: "#f59e0b" },
    { type: "docx", color: "#3b82f6" },
    { type: "text", color: "#0ea5e9" },
];

export default function GraphPage() {
    const [graph, setGraph] = useState<GraphData | null>(null);
    const [selected, setSelected] = useState<GraphNode | null>(null);
    const [error, setError] = useState("");

    const load = () => {
        api.get<GraphData>("/api/graph").then(setGraph).catch((e) => setError(e.message));
    };

    useEffect(load, []);

    if (error) return <p className="text-sm text-red-500">{error}</p>;
    if (!graph) {
        return (
            <div className="flex h-64 items-center justify-center">
                <Loader2 className="h-7 w-7 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <header className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h1 className="flex items-center gap-2 text-2xl font-bold">
                        <Network className="h-6 w-6 text-primary" /> Knowledge Graph
                    </h1>
                    <p className="text-sm text-muted-foreground">
                        {graph.nodes.length} documents · {graph.edges.length} AI-discovered connections
                    </p>
                </div>
                <button onClick={load} className="flex items-center gap-2 rounded-lg border px-3.5 py-2 text-sm font-medium hover:bg-muted">
                    <RefreshCw className="h-4 w-4" /> Rebuild view
                </button>
            </header>

            <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
                <div className="relative h-[60vh] min-h-[420px] overflow-hidden rounded-xl border bg-card lg:h-[calc(100vh-16rem)]">
                    <GraphCanvas graph={graph} selectedId={selected?.id} onSelect={setSelected} />
                    <div className="absolute bottom-3 left-3 flex flex-wrap gap-2 rounded-lg border bg-background/80 px-3 py-2 backdrop-blur">
                        {LEGEND.map((l) => (
                            <span key={l.type} className="flex items-center gap-1.5 text-[11px] capitalize text-muted-foreground">
                                <span className="h-2.5 w-2.5 rounded-full" style={{ background: l.color }} />
                                {l.type}
                            </span>
                        ))}
                    </div>
                    <p className="absolute right-3 top-3 rounded-lg bg-background/80 px-2.5 py-1 text-[11px] text-muted-foreground backdrop-blur">
                        drag nodes · scroll to zoom · drag background to pan
                    </p>
                </div>

                <aside className="rounded-xl border bg-card p-5">
                    {!selected ? (
                        <div className="flex h-full flex-col items-center justify-center gap-2 py-10 text-center">
                            <Network className="h-7 w-7 text-muted-foreground" />
                            <p className="text-sm font-medium">Select a node</p>
                            <p className="max-w-[200px] text-xs text-muted-foreground">
                                Click any document to see its details and connections.
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-4 animate-fade-in">
                            <span className={`inline-flex rounded-md px-2 py-0.5 text-xs font-medium uppercase`}>
                                {selected.file_type}
                            </span>
                            <h3 className="text-lg font-bold leading-snug">{selected.label}</h3>
                            <p className="text-sm leading-relaxed text-muted-foreground">{selected.summary || "No summary yet."}</p>
                            {selected.tags.length > 0 && (
                                <div className="flex flex-wrap gap-1.5">
                                    {selected.tags.map((t) => (
                                        <span key={t} className="rounded-full bg-muted px-2 py-0.5 text-[11px]">#{t}</span>
                                    ))}
                                </div>
                            )}
                            <Link
                                href={`/documents/${selected.id}`}
                                className="flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
                            >
                                Open document <ArrowUpRight className="h-4 w-4" />
                            </Link>
                        </div>
                    )}
                </aside>
            </div>
        </div>
    );
}
