"use client";

import { useState } from "react";
import { Plus, Trash2, ChevronLeft, ChevronRight, CalendarDays, Bot } from "lucide-react";
import { api } from "@/lib/api";
import type { Task } from "@/lib/types";

const COLUMNS: { status: Task["status"]; label: string }[] = [
    { status: "todo", label: "To Do" },
    { status: "in_progress", label: "In Progress" },
    { status: "done", label: "Done" },
];

const PRIORITY_CLS: Record<Task["priority"], string> = {
    high: "bg-red-500/10 text-red-500",
    medium: "bg-amber-500/10 text-amber-500",
    low: "bg-sky-500/10 text-sky-500",
};

export default function TaskBoard({
    tasks,
    onChange,
}: {
    tasks: Task[];
    onChange: () => void;
}) {
    const [creating, setCreating] = useState(false);
    const [title, setTitle] = useState("");
    const [priority, setPriority] = useState<Task["priority"]>("medium");
    const [dueDate, setDueDate] = useState("");
    const [busy, setBusy] = useState(false);

    const create = async (status: Task["status"]) => {
        if (!title.trim() || busy) return;
        setBusy(true);
        try {
            await api.post("/api/tasks", { title: title.trim(), priority, due_date: dueDate });
            setTitle("");
            setDueDate("");
            setCreating(false);
            onChange();
        } finally {
            setBusy(false);
        }
    };

    const move = async (task: Task, dir: -1 | 1) => {
        const order: Task["status"][] = ["todo", "in_progress", "done"];
        const next = order[order.indexOf(task.status) + dir];
        if (!next) return;
        await api.patch(`/api/tasks/${task.id}`, { status: next });
        onChange();
    };

    const remove = async (id: string) => {
        await api.delete(`/api/tasks/${id}`);
        onChange();
    };

    return (
        <div>
            <div className="mb-4 flex justify-end">
                <button
                    onClick={() => setCreating(!creating)}
                    className="flex items-center gap-2 rounded-lg bg-primary px-3.5 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
                >
                    <Plus className="h-4 w-4" /> New task
                </button>
            </div>

            {creating && (
                <div className="mb-4 grid gap-2 rounded-xl border bg-card p-4 animate-fade-in md:grid-cols-[1fr_auto_auto_auto]">
                    <input
                        autoFocus
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && create("todo")}
                        placeholder="Task title"
                        className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                    />
                    <select
                        value={priority}
                        onChange={(e) => setPriority(e.target.value as Task["priority"])}
                        className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                    >
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                    </select>
                    <input
                        type="date"
                        value={dueDate}
                        onChange={(e) => setDueDate(e.target.value)}
                        className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                    />
                    <button
                        onClick={() => create("todo")}
                        disabled={!title.trim() || busy}
                        className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-40"
                    >
                        Add
                    </button>
                </div>
            )}

            <div className="grid gap-4 lg:grid-cols-3">
                {COLUMNS.map((col, ci) => {
                    const items = tasks.filter((t) => t.status === col.status);
                    return (
                        <div key={col.status} className="rounded-xl border bg-muted/30 p-3">
                            <p className="mb-3 flex items-center justify-between px-1 text-sm font-semibold">
                                {col.label}
                                <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">{items.length}</span>
                            </p>
                            <div className="space-y-2">
                                {items.map((t) => (
                                    <div key={t.id} className="group rounded-lg border bg-card p-3 shadow-sm animate-fade-in">
                                        <div className="flex items-start justify-between gap-2">
                                            <p className={`text-sm font-medium ${t.status === "done" ? "line-through opacity-60" : ""}`}>
                                                {t.title}
                                            </p>
                                            <button
                                                onClick={() => remove(t.id)}
                                                className="opacity-0 transition-opacity group-hover:opacity-100"
                                                aria-label="Delete task"
                                            >
                                                <Trash2 className="h-3.5 w-3.5 text-muted-foreground hover:text-red-500" />
                                            </button>
                                        </div>
                                        {t.description && (
                                            <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{t.description}</p>
                                        )}
                                        <div className="mt-2 flex flex-wrap items-center gap-1.5">
                                            <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${PRIORITY_CLS[t.priority]}`}>
                                                {t.priority}
                                            </span>
                                            {t.source === "ai_plan" && (
                                                <span className="flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
                                                    <Bot className="h-3 w-3" /> AI plan
                                                </span>
                                            )}
                                            {t.due_date && (
                                                <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                                                    <CalendarDays className="h-3 w-3" /> {t.due_date}
                                                </span>
                                            )}
                                            <span className="ml-auto flex gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
                                                {ci > 0 && (
                                                    <button onClick={() => move(t, -1)} aria-label="Move back" className="rounded p-1 hover:bg-muted">
                                                        <ChevronLeft className="h-3.5 w-3.5" />
                                                    </button>
                                                )}
                                                {ci < 2 && (
                                                    <button onClick={() => move(t, 1)} aria-label="Move forward" className="rounded p-1 hover:bg-muted">
                                                        <ChevronRight className="h-3.5 w-3.5" />
                                                    </button>
                                                )}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                                {items.length === 0 && (
                                    <p className="py-6 text-center text-xs text-muted-foreground">Nothing here yet</p>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
