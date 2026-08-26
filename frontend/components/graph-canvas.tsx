"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Graph, GraphNode } from "@/lib/types";

interface SimNode extends GraphNode {
    x: number;
    y: number;
    vx: number;
    vy: number;
    fixed: boolean;
}

const W = 900;
const H = 560;

const TYPE_FILL: Record<string, string> = {
    pdf: "#ef4444",
    code: "#10b981",
    image: "#8b5cf6",
    note: "#f59e0b",
    docx: "#3b82f6",
    text: "#0ea5e9",
};

export default function GraphCanvas({
    graph,
    selectedId,
    onSelect,
}: {
    graph: Graph;
    selectedId?: string | null;
    onSelect?: (node: GraphNode) => void;
}) {
    const nodesRef = useRef<SimNode[]>([]);
    const edgesRef = useRef<{ a: SimNode; b: SimNode; similarity: number }[]>([]);
    const alphaRef = useRef(1);
    const rafRef = useRef(0);
    const [, setTick] = useState(0);
    const [view, setView] = useState({ k: 1, x: 0, y: 0 });
    const dragNodeRef = useRef<SimNode | null>(null);
    const panRef = useRef<{ sx: number; sy: number; ox: number; oy: number } | null>(null);

    if (nodesRef.current.length !== graph.nodes.length) {
        const prev = new Map(nodesRef.current.map((n) => [n.id, n]));
        nodesRef.current = graph.nodes.map((n, i) => {
            const old = prev.get(n.id);
            const angle = (i / Math.max(graph.nodes.length, 1)) * Math.PI * 2;
            return {
                ...n,
                x: old?.x ?? W / 2 + Math.cos(angle) * 180,
                y: old?.y ?? H / 2 + Math.sin(angle) * 180,
                vx: 0,
                vy: 0,
                fixed: false,
            };
        });
        alphaRef.current = 1;
    }
    if (edgesRef.current.length !== graph.edges.length) {
        const byId = new Map(nodesRef.current.map((n) => [n.id, n]));
        edgesRef.current = graph.edges
            .map((e) => ({ a: byId.get(e.source), b: byId.get(e.target), similarity: e.similarity }))
            .filter((e): e is { a: SimNode; b: SimNode; similarity: number } => !!(e.a && e.b));
    }

    useEffect(() => {
        const step = () => {
            const nodes = nodesRef.current;
            const edges = edgesRef.current;
            const alpha = alphaRef.current;
            if (alpha > 0.004 && nodes.length > 0) {
                for (let i = 0; i < nodes.length; i++) {
                    const a = nodes[i];
                    for (let j = i + 1; j < nodes.length; j++) {
                        const b = nodes[j];
                        let dx = b.x - a.x;
                        let dy = b.y - a.y;
                        let d2 = dx * dx + dy * dy;
                        if (d2 < 1) { dx = Math.random() - 0.5; dy = Math.random() - 0.5; d2 = 1; }
                        const repulse = 9000 / d2;
                        const d = Math.sqrt(d2);
                        const fx = (dx / d) * repulse * alpha;
                        const fy = (dy / d) * repulse * alpha;
                        a.vx -= fx; a.vy -= fy;
                        b.vx += fx; b.vy += fy;
                    }
                    a.vx += (W / 2 - a.x) * 0.003 * alpha;
                    a.vy += (H / 2 - a.y) * 0.003 * alpha;
                }
                for (const e of edges) {
                    const target = 130 - e.similarity * 40;
                    let dx = e.b.x - e.a.x;
                    let dy = e.b.y - e.a.y;
                    const d = Math.sqrt(dx * dx + dy * dy) || 1;
                    const f = ((d - target) / d) * 0.02 * alpha;
                    dx *= f; dy *= f;
                    e.a.vx += dx; e.a.vy += dy;
                    e.b.vx -= dx; e.b.vy -= dy;
                }
                for (const n of nodes) {
                    if (!n.fixed) {
                        n.vx *= 0.82; n.vy *= 0.82;
                        n.x += Math.max(-30, Math.min(30, n.vx));
                        n.y += Math.max(-30, Math.min(30, n.vy));
                    } else {
                        n.vx = 0; n.vy = 0;
                    }
                }
                alphaRef.current = alpha * 0.985;
                setTick((t) => t + 1);
            }
            rafRef.current = requestAnimationFrame(step);
        };
        rafRef.current = requestAnimationFrame(step);
        return () => cancelAnimationFrame(rafRef.current);
    }, []);

    const toWorld = useCallback(
        (clientX: number, clientY: number, svg: SVGSVGElement) => {
            const rect = svg.getBoundingClientRect();
            return {
                x: (clientX - rect.left - view.x) / view.k,
                y: (clientY - rect.top - view.y) / view.k,
            };
        },
        [view]
    );

    const onPointerDown = (e: React.PointerEvent<SVGSVGElement>) => {
        const svg = e.currentTarget;
        const { x, y } = toWorld(e.clientX, e.clientY, svg);
        const hit = [...nodesRef.current].reverse().find((n) => {
            const dx = n.x - x, dy = n.y - y;
            return dx * dx + dy * dy < 26 * 26;
        });
        if (hit) {
            dragNodeRef.current = hit;
            hit.fixed = true;
        } else {
            panRef.current = { sx: e.clientX, sy: e.clientY, ox: view.x, oy: view.y };
        }
        svg.setPointerCapture(e.pointerId);
    };

    const onPointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
        if (dragNodeRef.current) {
            const { x, y } = toWorld(e.clientX, e.clientY, e.currentTarget);
            dragNodeRef.current.x = x;
            dragNodeRef.current.y = y;
            alphaRef.current = Math.max(alphaRef.current, 0.3);
            setTick((t) => t + 1);
        } else if (panRef.current) {
            const p = panRef.current;
            setView((v) => ({ ...v, x: p.ox + (e.clientX - p.sx), y: p.oy + (e.clientY - p.sy) }));
        }
    };

    const onPointerUp = () => {
        if (dragNodeRef.current) {
            dragNodeRef.current.fixed = false;
            dragNodeRef.current = null;
        }
        panRef.current = null;
    };

    const radiusFor = (n: SimNode) =>
        Math.min(26, 12 + Math.sqrt(n.summary.length || n.tags.length || 3));

    return (
        <svg
            viewBox={`0 0 ${W} ${H}`}
            className="h-full w-full touch-none select-none"
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onWheel={(e) => {
                e.preventDefault();
                setView((v) => ({
                    ...v,
                    k: Math.min(3, Math.max(0.4, v.k * (e.deltaY > 0 ? 0.92 : 1.08))),
                }));
            }}
        >
            <defs>
                <radialGradient id="glow" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.25" />
                    <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0" />
                </radialGradient>
            </defs>
            <g transform={`translate(${view.x},${view.y}) scale(${view.k})`}>
                {graph.nodes.length === 0 && (
                    <text x={W / 2} y={H / 2} textAnchor="middle" className="fill-muted-foreground text-sm">
                        No documents yet — upload files to grow your knowledge graph
                    </text>
                )}
                {edgesRef.current.map((e, i) => (
                    <line
                        key={i}
                        x1={e.a.x} y1={e.a.y} x2={e.b.x} y2={e.b.y}
                        stroke="hsl(var(--primary))"
                        strokeOpacity={0.15 + e.similarity * 0.45}
                        strokeWidth={1 + e.similarity * 2}
                    />
                ))}
                {nodesRef.current.map((n) => {
                    const r = radiusFor(n);
                    const selected = selectedId === n.id;
                    return (
                        <g
                            key={n.id}
                            transform={`translate(${n.x},${n.y})`}
                            className="cursor-pointer"
                            style={{ transition: "opacity 0.2s" }}
                        >
                            {selected && <circle r={r + 16} fill="url(#glow)" />}
                            <circle
                                r={r}
                                fill={TYPE_FILL[n.file_type] || TYPE_FILL.text}
                                fillOpacity={selected ? 1 : 0.8}
                                stroke={selected ? "hsl(var(--foreground))" : "transparent"}
                                strokeWidth={2.5}
                            />
                            <text
                                y={r + 14}
                                textAnchor="middle"
                                className="fill-foreground text-[11px] font-medium pointer-events-none"
                                style={{ paintOrder: "stroke", stroke: "hsl(var(--background))", strokeWidth: 3 }}
                            >
                                {n.label.length > 22 ? n.label.slice(0, 20) + "…" : n.label}
                            </text>
                        </g>
                    );
                })}
            </g>
        </svg>
    );
}
