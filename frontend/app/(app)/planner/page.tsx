"use client";

import { useCallback, useEffect, useState } from "react";
import { CalendarCheck, Loader2, Sparkles, Bot } from "lucide-react";
import { api } from "@/lib/api";
import type { Task, Document } from "@/lib/types";
import TaskBoard from "@/components/task-board";

export default function PlannerPage() {
    const [tasks, setTasks] = useState<Task[] | null>(null);
    const [docs, setDocs] = useState<Document[]>([]);
    const [goal, setGoal] = useState("");
    const [days, setDays] = useState(7);
    const [hours, setHours] = useState(2);
    const [docId, setDocId] = useState("");
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState("");

    const loadTasks = useCallback(() => {
        api.get<Task[]>("/api/tasks").then(setTasks);
    }, []);

    useEffect(() => {
        loadTasks();
        api.get<Document[]>("/api/documents")
            .then((d) => setDocs(d.filter((x) => x.status === "ready")))
            .catch(() => {});
    }, [loadTasks]);

    const generatePlan = async () => {
        if (!goal.trim() || generating) return;
        setGenerating(true);
        setError("");
        try {
            await api.post("/api/tasks/study-plan", {
                goal: goal.trim(),
                days,
                hours_per_day: hours,
                document_id: docId || undefined,
            });
            setGoal("");
            loadTasks();
        } catch (e) {
            setError(e instanceof Error ? e.message : "Plan generation failed");
        } finally {
            setGenerating(false);
        }
    };

    return (
        <div className="space-y-6">
            <header>
                <h1 className="flex items-center gap-2 text-2xl font-bold">
                    <CalendarCheck className="h-6 w-6 text-primary" /> Task Planner
                </h1>
                <p className="text-sm text-muted-foreground">Track work and let AI build day-by-day study plans</p>
            </header>

            <section className="space-y-3 rounded-xl border bg-card p-5">
                <h2 className="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
                    <Sparkles className="h-4 w-4 text-primary" /> AI STUDY PLAN GENERATOR
                </h2>
                <div className="grid gap-3 md:grid-cols-[1fr_100px_110px_1fr_auto]">
                    <input
                        value={goal}
                        onChange={(e) => setGoal(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && generatePlan()}
                        placeholder="e.g. Master distributed systems for system design interviews"
                        className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                    />
                    <label className="flex items-center gap-2 rounded-lg border bg-background px-3 text-sm">
                        Days
                        <input
                            type="number"
                            min={1}
                            max={60}
                            value={days}
                            onChange={(e) => setDays(Math.max(1, Math.min(60, Number(e.target.value) || 1)))}
                            className="w-full bg-transparent outline-none"
                        />
                    </label>
                    <label className="flex items-center gap-2 rounded-lg border bg-background px-3 text-sm">
                        h/day
                        <input
                            type="number"
                            min={0.5}
                            max={12}
                            step={0.5}
                            value={hours}
                            onChange={(e) => setHours(Math.max(0.5, Math.min(12, Number(e.target.value) || 2)))}
                            className="w-full bg-transparent outline-none"
                        />
                    </label>
                    <select
                        value={docId}
                        onChange={(e) => setDocId(e.target.value)}
                        className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                    >
                        <option value="">Ground in knowledge base (optional)</option>
                        {docs.map((d) => (
                            <option key={d.id} value={d.id}>{d.title}</option>
                        ))}
                    </select>
                    <button
                        onClick={generatePlan}
                        disabled={!goal.trim() || generating}
                        className="flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2 text-sm font-medium text-primary-foreground disabled:opacity-40"
                    >
                        {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Bot className="h-4 w-4" />}
                        Generate
                    </button>
                </div>
                {error && <p className="text-sm text-red-500">{error}</p>}
                <p className="text-xs text-muted-foreground">
                    The AI retrieves related material from your knowledge base and creates prioritized daily tasks.
                </p>
            </section>

            {tasks === null ? (
                <Loader2 className="mx-auto h-7 w-7 animate-spin text-primary" />
            ) : (
                <TaskBoard tasks={tasks} onChange={loadTasks} />
            )}
        </div>
    );
}
