import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { ThemeProvider } from "@/components/theme-provider";

export const metadata: Metadata = {
    title: "Second Brain OS — AI-Powered Knowledge Platform",
    description:
        "Upload documents, build a searchable knowledge graph, chat with your knowledge base, generate flashcards and study plans.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en" suppressHydrationWarning>
            <body className="min-h-screen antialiased">
                <ThemeProvider>
                    <AuthProvider>{children}</AuthProvider>
                </ThemeProvider>
            </body>
        </html>
    );
}
