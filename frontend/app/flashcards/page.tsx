"use client";

import { useCallback, useEffect, useState } from "react";
import { Layers, Loader2, Plus, Trash2, GraduationCap } from "lucide-react";
import { api } from "@/lib/api";
import type { Deck, DeckDetail, Document, Flashcard } from "@/lib/types";
import FlashcardReview from "@/components/flashcard-review";

export default function FlashcardsPage() {
    const [decks, setDecks] = useState<Deck[] | null>(null);
    const [docs, setDocs] = useState<Document[]>([]);
    const [activeDeck, setActiveDeck] = useState<DeckDetail | null>(null);
    const [reviewQueue, setReviewQueue] = useState<Flashcard[] | null>(null);
    const [genDocId, setGenDocId] = useState("");
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");

    const loadDecks = useCallback(() => {
        api.get<Deck[]>("/api/flashcards/decks").then(setDecks);
    }, []);

    useEffect(() => {
        loadDecks();
        api.get<Document[]>("/api/documents")
            .then((d) => setDocs(d.filter((x) => x.status === "ready")))
            .catch(() => {});
    }, [loadDecks]);

    const openDeck = async (deck: Deck) => {
        setActiveDeck(null);
        setReviewQueue(null);
        const detail = await api.get<DeckDetail>(`/api/flashcards/decks/${deck.id}`);
        setActiveDeck(detail);
    };

    const startReview = async (deckId: string, forceAll = false) => {
        const cards = forceAll
            ? (await api.get<DeckDetail>(`/api/flashcards/decks/${deckId}`)).cards
            : await api.get<Flashcard[]>(`/api/flashcards/decks/${deckId}/due`);
        if (!forceAll && cards.length === 0) return;
        setReviewQueue(cards);
    };

    const reviewCard = async (cardId: string, quality: number) => {
        await api.post(`/api/flashcards/cards/${cardId}/review`, { quality });
        loadDecks();
    };

    const generate = async () => {
        if (!genDocId || busy) return;
        setBusy(true);
        setError("");
        try {
            const deck = await api.post<DeckDetail>("/api/flashcards/generate", {
                document_id: genDocId,
                count: 10,
            });
            setGenDocId("");
            loadDecks();
            setActiveDeck(deck);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Generation failed");
        } finally {
            setBusy(false);
        }
    };

    const deleteDeck = async (id: string) => {
        await api.delete(`/api/flashcards/decks/${id}`);
        if (activeDeck?.id === id) {
            setActiveDeck(null);
            setReviewQueue(null);
        }
        loadDecks();
    };

    if (reviewQueue) {
        return (
            <div className="space-y-4">
                <button onClick={() => setReviewQueue(null)} className="text-sm text-muted-foreground hover:text-primary">
                    ← Exit review
                </button>
                <h1 className="text-xl font-bold">{activeDeck?.title}</h1>
                <div className="rounded-2xl border bg-card p-4">
                    <FlashcardReview
                        queue={reviewQueue}
                        onReviewed={reviewCard}
                        onRestart={() =>
                            activeDeck &&
                            api.get<DeckDetail>(`/api/flashcards/decks/${activeDeck.id}`)
                                .then((d) => {
                                    setActiveDeck(d);
                                    setReviewQueue(d.cards);
                                })
                        }
                    />
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <header>
                <h1 className="flex items-center gap-2 text-2xl font-bold">
                    <Layers className="h-6 w-6 text-primary" /> Flashcards
                </h1>
                <p className="text-sm text-muted-foreground">
                    Auto-generated study decks with SM-2 spaced repetition
                </p>
            </header>

            <section className="flex flex-wrap items-center gap-2 rounded-xl border bg-card p-4">
                <Plus className="h-4 w-4 text-primary" />
                <select
                    value={genDocId}
                    onChange={(e) => setGenDocId(e.target.value)}
                    className="min-w-[220px] flex-1 rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                >
                    <option value="">Choose a document…</option>
                    {docs.map((d) => (
                        <option key={d.id} value={d.id}>{d.title}</option>
                    ))}
                </select>
                <button
                    onClick={generate}
                    disabled={!genDocId || busy}
                    className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-40"
                >
                    {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Generate deck"}
                </button>
            </section>
            {error && <p className="text-sm text-red-500">{error}</p>}

            {decks === null ? (
                <Loader2 className="mx-auto h-7 w-7 animate-spin text-primary" />
            ) : decks.length === 0 ? (
                <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed py-16 text-center">
                    <GraduationCap className="h-8 w-8 text-muted-foreground" />
                    <p className="font-medium">No decks yet</p>
                    <p className="max-w-xs text-sm text-muted-foreground">
                        Pick a document above and the AI will turn its key ideas into flashcards.
                    </p>
                </div>
            ) : (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {decks.map((d) => (
                        <div key={d.id} className="group flex flex-col rounded-xl border bg-card p-5 transition-all hover:border-primary/40 hover:shadow-md">
                            <div className="flex items-start justify-between gap-2">
                                <h3 className="line-clamp-2 flex-1 font-semibold">{d.title}</h3>
                                <button onClick={() => deleteDeck(d.id)} aria-label="Delete deck"
                                    className="opacity-0 transition-opacity group-hover:opacity-100">
                                    <Trash2 className="h-4 w-4 text-muted-foreground hover:text-red-500" />
                                </button>
                            </div>
                            <p className="mt-1 text-sm text-muted-foreground">
                                {d.card_count} cards · {new Date(d.created_at).toLocaleDateString()}
                            </p>
                            <div className="mt-4 flex gap-2">
                                <button
                                    onClick={() => openDeck(d)}
                                    className="flex-1 rounded-lg border py-2 text-sm font-medium hover:bg-muted"
                                >
                                    Browse
                                </button>
                                {d.due_count > 0 ? (
                                    <button
                                        onClick={() => { openDeck(d).then(() => startReview(d.id)); }}
                                        className="flex-1 rounded-lg bg-primary py-2 text-sm font-semibold text-primary-foreground hover:opacity-90"
                                    >
                                        Review ({d.due_count})
                                    </button>
                                ) : (
                                    <button
                                        onClick={() => startReview(d.id, true)}
                                        className="flex-1 rounded-lg border border-primary/40 py-2 text-sm font-medium text-primary hover:bg-primary/10"
                                    >
                                        Practice all
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {activeDeck && !reviewQueue && (
                <section className="space-y-2 rounded-xl border bg-card p-5">
                    <h2 className="font-semibold">{activeDeck.title}</h2>
                    <div className="grid max-h-80 gap-2 overflow-y-auto pr-1 sm:grid-cols-2">
                        {activeDeck.cards.map((c) => (
                            <div key={c.id} className="rounded-lg border p-3 text-sm">
                                <p className="font-medium">{c.front}</p>
                                <p className="mt-1 line-clamp-2 text-muted-foreground">{c.back}</p>
                            </div>
                        ))}
                    </div>
                </section>
            )}
        </div>
    );
}
