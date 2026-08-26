"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
    Brain, LayoutDashboard, FileText, Search, MessageSquare, Network,
    Layers, CalendarCheck, LogOut, Moon, Sun, Menu, X, Loader2,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/components/theme-provider";

const nav = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/documents", label: "Documents", icon: FileText },
    { href: "/search", label: "Search", icon: Search },
    { href: "/chat", label: "AI Chat", icon: MessageSquare },
    { href: "/graph", label: "Knowledge Graph", icon: Network },
    { href: "/flashcards", label: "Flashcards", icon: Layers },
    { href: "/planner", label: "Task Planner", icon: CalendarCheck },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
    const { user, loading, logout } = useAuth();
    const { theme, toggle } = useTheme();
    const router = useRouter();
    const pathname = usePathname();
    const [mobileOpen, setMobileOpen] = useState(false);

    useEffect(() => {
        if (!loading && !user) router.push("/auth/login");
    }, [loading, user, router]);

    if (loading || !user) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    const sidebar = (
        <div className="flex h-full flex-col">
            <Link href="/dashboard" className="flex h-16 items-center gap-2 border-b px-5 font-semibold">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                    <Brain className="h-5 w-5" />
                </div>
                Second Brain OS
            </Link>
            <nav className="flex-1 space-y-1 overflow-y-auto p-3">
                {nav.map((item) => {
                    const active = pathname === item.href || pathname.startsWith(item.href + "/");
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            onClick={() => setMobileOpen(false)}
                            className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${active
                                    ? "bg-primary/10 text-primary"
                                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                                }`}
                        >
                            <item.icon className="h-4 w-4" />
                            {item.label}
                        </Link>
                    );
                })}
            </nav>
            <div className="border-t p-3">
                <div className="mb-2 flex items-center gap-3 rounded-lg px-3 py-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/15 text-sm font-semibold text-primary">
                        {user.name.charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{user.name}</p>
                        <p className="truncate text-xs text-muted-foreground">{user.email}</p>
                    </div>
                </div>
                <div className="flex gap-1">
                    <button
                        onClick={toggle}
                        className="flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-muted"
                    >
                        {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                        {theme === "dark" ? "Light" : "Dark"}
                    </button>
                    <button
                        onClick={logout}
                        className="flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-red-500"
                    >
                        <LogOut className="h-4 w-4" />
                        Logout
                    </button>
                </div>
            </div>
        </div>
    );

    return (
        <div className="flex min-h-screen">
            {/* Desktop sidebar */}
            <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r bg-card lg:block">
                {sidebar}
            </aside>

            {/* Mobile sidebar */}
            {mobileOpen && (
                <div className="fixed inset-0 z-50 lg:hidden">
                    <div className="absolute inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
                    <aside className="absolute inset-y-0 left-0 w-64 border-r bg-card">{sidebar}</aside>
                </div>
            )}

            <div className="flex min-h-screen flex-1 flex-col lg:pl-64">
                {/* Mobile topbar */}
                <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b bg-card px-4 lg:hidden">
                    <button onClick={() => setMobileOpen(true)} className="rounded-lg p-2 hover:bg-muted">
                        {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
                    </button>
                    <span className="text-sm font-semibold">
                        {nav.find((n) => pathname.startsWith(n.href))?.label || "Second Brain OS"}
                    </span>
                    <div className="w-9" />
                </header>
                <main className="flex-1 p-4 md:p-6 lg:p-8">{children}</main>
            </div>
        </div>
    );
}
