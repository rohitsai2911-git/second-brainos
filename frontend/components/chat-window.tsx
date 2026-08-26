"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { Send, Loader2, Sparkles, FileText } from "lucide-react";
import { api } from "@/lib/api";
import type { Conversation, ConversationDetail, Message } from "@/lib/types";

export default function ChatWindow({
    conversations,
    activeId,
    onCreated,
    onSelect,
}: {
    conversations: Conversation[];
    activeId: string | null;
    onCreated?: (conv: Conversation) => void;
    onSelect?: (id: string) => void;
}) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [sending, setSending] = useState(false);
    const [error, setError] = useState("");
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!activeId) {
            setMessages([]);
            return;
        }
        api.get<ConversationDetail>(`/api/chat/conversations/${activeId}`)
            .then((c) => setMessages(c.messages))
            .catch(() => setMessages([]));
    }, [activeId]);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, sending]);

    const send = async () => {
        const text = input.trim();
        if (!text || sending) return;
        setInput("");
        setError("");
        setSending(true);
        const optimistic: Message = {
            id: `tmp-${Date.now()}`,
            role: "user",
            content: text,
            sources: [],
            created_at: new Date().toISOString(),
        };
        setMessages((m) => [...m, optimistic]);
        try {
            const res = await api.post<{ conversation_id: string; message: Message }>(
                "/api/chat",
                { message: text, conversation_id: activeId }
            );
            if (!activeId && onCreated) {
                const conv = conversations.find((c) => c.id === res.conversation_id);
                if (conv) onCreated(conv);
                else onCreated({ id: res.conversation_id, title: text.slice(0, 60), created_at: new Date().toISOString() });
                onSelect?.(res.conversation_id);
            }
            setMessages((m) => [...m.filter((x) => x.id !== optimistic.id), res.message]);
        } catch (e) {
            setMessages((m) => m.filter((x) => x.id !== optimistic.id));
            setError(e instanceof Error ? e.message : "Failed to send");
        } finally {
            setSending(false);
        }
    };

    return (
        <div className="flex h-full flex-col">
            <div className="flex-1 space-y-4 overflow-y-auto p-4 md:p-6">
                {messages.length === 0 && !sending && (
                    <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
                        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                            <Sparkles className="h-7 w-7" />
                        </div>
                        <h3 className="text-lg font-semibold">Ask your second brain</h3>
                        <p className="max-w-sm text-sm text-muted-foreground">
                            Questions are answered from your own documents with citations.
                            Tell me things like "remember that I'm preparing for ML interviews".
                        </p>
                    </div>
                )}
                {messages.map((m) => (
                    <div key={m.id} className={`flex animate-fade-in ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                        <div
                            className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm md:max-w-[75%] ${
                                m.role === "user"
                                    ? "bg-primary text-primary-foreground"
                                    : "border bg-card prose-sbo"
                            }`}
                        >
                            {m.role === "user" ? (
                                <p className="whitespace-pre-wrap">{m.content}</p>
                            ) : (
                                <>
                                    <ReactMarkdown>{m.content}</ReactMarkdown>
                                    {m.sources?.length > 0 && (
                                        <div className="mt-3 flex flex-wrap gap-1.5 border-t pt-2">
                                            {m.sources.map((s, i) => (
                                                <Link
                                                    key={i}
                                                    href={`/documents/${s.document_id}`}
                                                    className="flex max-w-[240px] items-center gap-1 truncate rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground hover:text-primary"
                                                    title={s.snippet}
                                                >
                                                    <FileText className="h-3 w-3 shrink-0" />
                                                    <span className="truncate">{s.document_title}</span>
                                                    <span className="shrink-0 opacity-60">{Math.round(s.score * 100)}%</span>
                                                </Link>
                                            ))}
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                    </div>
                ))}
                {sending && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                        Thinking through your knowledge base…
                    </div>
                )}
                {error && <p className="text-sm text-red-500">{error}</p>}
                <div ref={bottomRef} />
            </div>
            <div className="border-t bg-card p-3 md:p-4">
                <div className="flex items-end gap-2">
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault();
                                send();
                            }
                        }}
                        rows={1}
                        placeholder="Ask anything about your knowledge…"
                        className="max-h-40 flex-1 resize-none rounded-xl border bg-background px-4 py-3 text-sm outline-none focus:border-primary"
                    />
                    <button
                        onClick={send}
                        disabled={sending || !input.trim()}
                        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground transition-opacity disabled:opacity-40"
                        aria-label="Send message"
                    >
                        <Send className="h-4 w-4" />
                    </button>
                </div>
            </div>
        </div>
    );
}
