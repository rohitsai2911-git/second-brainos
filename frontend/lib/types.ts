export interface User {
    id: string;
    email: string;
    name: string;
    created_at: string;
}

export interface Document {
    id: string;
    title: string;
    filename: string;
    file_type: string;
    mime_type: string;
    size_bytes: number;
    summary: string;
    tags: string[];
    status: "processing" | "ready" | "error";
    processing_stage: string;
    error_message: string;
    processing_warning: string;
    created_at: string;
}

export interface DocumentDetail extends Document {
    content_text: string;
}

export interface SearchResult {
    chunk_id: string;
    document_id: string;
    document_title: string;
    file_type: string;
    text: string;
    score: number;
}

export interface Source {
    document_id: string;
    document_title: string;
    chunk_id: string;
    score: number;
    snippet: string;
}

export interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    sources: Source[];
    created_at: string;
}

export interface Conversation {
    id: string;
    title: string;
    created_at: string;
}

export interface ConversationDetail extends Conversation {
    messages: Message[];
}

export interface Flashcard {
    id: string;
    front: string;
    back: string;
    ease: number;
    interval_days: number;
    repetitions: number;
    due_at: string;
}

export interface Deck {
    id: string;
    title: string;
    document_id: string | null;
    created_at: string;
    card_count: number;
    due_count: number;
}

export interface DeckDetail extends Deck {
    cards: Flashcard[];
}

export interface Task {
    id: string;
    title: string;
    description: string;
    status: "todo" | "in_progress" | "done";
    priority: "low" | "medium" | "high";
    due_date: string;
    source: string;
    created_at: string;
}

export interface GraphNode {
    id: string;
    label: string;
    file_type: string;
    tags: string[];
    summary: string;
}

export interface GraphEdge {
    source: string;
    target: string;
    similarity: number;
}

export interface Graph {
    nodes: GraphNode[];
    edges: GraphEdge[];
}

export interface Stats {
    total_documents: number;
    total_chunks: number;
    total_flashcards: number;
    due_flashcards: number;
    total_tasks: number;
    completed_tasks: number;
    total_memories: number;
    total_links: number;
    total_size_bytes: number;
    top_tags: string[];
    recent_documents: Document[];
}

export interface Memory {
    id: string;
    kind: string;
    content: string;
    created_at: string;
}
