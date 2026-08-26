import Link from "next/link";
import { LucideIcon } from "lucide-react";

export default function StatCard({
    icon: Icon,
    label,
    value,
    sub,
    href,
}: {
    icon: LucideIcon;
    label: string;
    value: string | number;
    sub?: string;
    href?: string;
}) {
    const body = (
        <div className="group flex items-center gap-4 rounded-xl border bg-card p-5 transition-all hover:border-primary/40 hover:shadow-md">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                <Icon className="h-5 w-5" />
            </div>
            <div className="min-w-0">
                <p className="text-2xl font-bold leading-tight">{value}</p>
                <p className="truncate text-sm text-muted-foreground">{sub || label}</p>
            </div>
        </div>
    );
    return href ? <Link href={href}>{body}</Link> : body;
}
