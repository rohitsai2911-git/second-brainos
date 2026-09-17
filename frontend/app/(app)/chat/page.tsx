"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, MessageSquare, Trash2, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import type { Conversation } from "@/lib/types";
import ChatWindow from "@/components/chat-window";

export default function ChatPage() {
    const [conversations, setConversations] = useState<Conversation[] | null>(null);
    const [activeId, setActiveId] = useState<string | null>(null);

    const load = useCallback(() => {
        api.get<Conversation[]>("/api/chat/conversations").then(setConversations);
    }, []);

    useEffect(load, [load]);

    useEffect(() => {
        const poll = setInterval(() => {
            if (!activeId) load();
        }, 3000);
        return () => clearInterval(poll);
    }, [activeId, load]);

    const newChat = () => setActiveId(null);

    const removeConversation = async (id: string) => {
        await api.delete(`/api/chat/conversations/${id}`);
        if (activeId === id) setActiveId(null);
        load();
    };

    return (
        <div className="flex h-[calc(100vh-7rem)] space-x-4 lg:h-[calc(100vh-9rem)]">
            <aside className="hidden w-64 shrink-0 flex-col rounded-xl border bg-card md:flex">
                <button
                    onClick={newChat}
                    className="m-3 flex items-center justify-center gap-2 rounded-lg bg-primary py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90"
                >
                    <Plus className="h-4 w-4" /> New conversation
                </button>
                <div className="flex-1 space-y-1 overflow-y-auto px-3 pb-3">
                    {conversations === null && (
                        <Loader2 className="mx-auto mt-6 h-5 w-5 animate-spin text-primary" />
                    )}
                    {conversations?.map((c) => (
                        <div
                            key={c.id}
                            className={`group flex items-center gap-1 rounded-lg px-2.5 py-2 text-sm transition-colors ${
                                activeId === c.id ? "bg-primary/10 text-primary" : "hover:bg-muted"
                            }`}
                        >
                            <MessageSquare className="h-3.5 w-3.5 shrink-0 opacity-60" />
                            <button onClick={() => setActiveId(c.id)} className="min-w-0 flex-1 truncate text-left">
                                {c.title}
                            </button>
                            <button
                                onClick={() => removeConversation(c.id)}
                                className="opacity-0 transition-opacity group-hover:opacity-100"
                                aria-label="Delete conversation"
                            >
                                <Trash2 className="h-3.5 w-3.5 text-muted-foreground hover:text-red-500" />
                            </button>
                        </div>
                    ))}
                </div>
            </aside>

            <main className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-xl border bg-card">
                <ChatWindow
                    conversations={conversations || []}
                    activeId={activeId}
                    onSelect={setActiveId}
                    onCreated={() => load()}
                />
            </main>
        </div>
    );
}
