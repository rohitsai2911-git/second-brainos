"use client";

import { useCallback, useRef, useState } from "react";
import { UploadCloud } from "lucide-react";

export default function UploadZone({
    onFiles,
    disabled,
}: {
    onFiles: (files: File[]) => void;
    disabled?: boolean;
}) {
    const [dragging, setDragging] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setDragging(false);
        if (!disabled) onFiles(Array.from(e.dataTransfer.files));
    }, [disabled, onFiles]);

    return (
        <div
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
                dragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50 hover:bg-muted/40"
            } ${disabled ? "pointer-events-none opacity-50" : ""}`}
        >
            <input
                ref={inputRef}
                type="file"
                multiple
                hidden
                onChange={(e) => {
                    onFiles(Array.from(e.target.files || []));
                    e.target.value = "";
                }}
            />
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
                <UploadCloud className="h-6 w-6" />
            </div>
            <p className="font-medium">
                Drop files here or <span className="text-primary">browse</span>
            </p>
            <p className="text-xs text-muted-foreground">
                PDFs, notes, code, images, documents · up to 100MB per file
            </p>
        </div>
    );
}
