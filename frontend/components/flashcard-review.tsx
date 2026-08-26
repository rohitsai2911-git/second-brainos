"use client";

import { useState } from "react";
import { RotateCcw, Eye } from "lucide-react";
import type { Flashcard } from "@/lib/types";

const GRADES = [
    { label: "Again", quality: 1, cls: "bg-red-500/10 text-red-500 hover:bg-red-500/20" },
    { label: "Hard", quality: 3, cls: "bg-amber-500/10 text-amber-500 hover:bg-amber-500/20" },
    { label: "Good", quality: 4, cls: "bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20" },
    { label: "Easy", quality: 5, cls: "bg-sky-500/10 text-sky-500 hover:bg-sky-500/20" },
];

export default function FlashcardReview({
    queue,
    onReviewed,
    onRestart,
}: {
    queue: Flashcard[];
    onReviewed: (cardId: string, quality: number) => void;
    onRestart?: () => void;
}) {
    const [index, setIndex] = useState(0);
    const [flipped, setFlipped] = useState(false);

    if (queue.length === 0) {
        return (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
                <p className="text-lg font-semibold">Nothing due right now</p>
                <p className="text-sm text-muted-foreground">Cards return as their spaced-repetition intervals elapse.</p>
                {onRestart && (
                    <button onClick={onRestart} className="mt-2 flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted">
                        <RotateCcw className="h-4 w-4" /> Practice anyway
                    </button>
                )}
            </div>
        );
    }

    const card = queue[index % queue.length];

    const grade = (quality: number) => {
        onReviewed(card.id, quality);
        setFlipped(false);
        if (index + 1 >= queue.length) {
            if (onRestart) onRestart();
            setIndex(0);
        } else {
            setIndex(index + 1);
        }
    };

    return (
        <div className="mx-auto flex max-w-xl flex-col items-center gap-6 py-6">
            <p className="text-sm text-muted-foreground">
                Card {index + 1} of {queue.length} · reviews: {card.repetitions}
            </p>
            <button
                onClick={() => setFlipped(!flipped)}
                className="relative h-64 w-full overflow-hidden rounded-2xl border bg-card p-8 text-left shadow-sm transition-colors hover:border-primary/40"
                aria-label="Flip card"
            >
                <div className={flipped ? "invisible" : "visible"}>
                    <p className="text-xs uppercase tracking-wide text-primary">Question</p>
                    <p className="mt-3 line-clamp-6 text-lg font-medium">{card.front}</p>
                    <p className="absolute bottom-5 right-8 text-xs text-muted-foreground">Click to reveal</p>
                </div>
                {flipped && (
                    <div className="animate-fade-in">
                        <p className="text-xs uppercase tracking-wide text-accent">Answer</p>
                        <p className="mt-3 max-h-44 overflow-y-auto text-base">{card.back}</p>
                    </div>
                )}
            </button>
            {!flipped ? (
                <button
                    onClick={() => setFlipped(true)}
                    className="flex items-center gap-2 rounded-xl bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground"
                >
                    <Eye className="h-4 w-4" /> Reveal answer
                </button>
            ) : (
                <div className="grid w-full grid-cols-4 gap-2">
                    {GRADES.map((g) => (
                        <button
                            key={g.quality}
                            onClick={() => grade(g.quality)}
                            className={`rounded-xl px-2 py-2.5 text-sm font-semibold transition-colors ${g.cls}`}
                        >
                            {g.label}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
