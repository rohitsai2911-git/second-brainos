const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("sbo_token");
}

export function setToken(token: string | null) {
    if (token) localStorage.setItem("sbo_token", token);
    else localStorage.removeItem("sbo_token");
}

async function request<T>(
    path: string,
    options: RequestInit = {},
    isForm = false
): Promise<T> {
    const headers: Record<string, string> = {};
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (!isForm) headers["Content-Type"] = "application/json";

    const res = await fetch(`${API_URL}${path}`, {
        ...options,
        headers: { ...headers, ...(options.headers as Record<string, string>) },
    });

    if (res.status === 401) {
        setToken(null);
        if (typeof window !== "undefined" && !window.location.pathname.startsWith("/auth")) {
            window.location.href = "/auth/login";
        }
        throw new Error("Unauthorized");
    }
    if (res.status === 204) return undefined as T;
    if (!res.ok) {
        let detail = `Request failed (${res.status})`;
        try {
            const body = await res.json();
            detail = body.detail || detail;
        } catch { }
        throw new Error(detail);
    }
    return res.json();
}

export const api = {
    get: <T>(path: string) => request<T>(path),
    post: <T>(path: string, body?: unknown) =>
        request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
    patch: <T>(path: string, body: unknown) =>
        request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
    delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
    upload: <T>(path: string, form: FormData) =>
        request<T>(path, { method: "POST", body: form }, true),
};

export { API_URL };
