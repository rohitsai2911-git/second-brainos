"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api, getToken, setToken } from "./api";
import type { User } from "./types";

interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (email: string, password: string) => Promise<void>;
    register: (name: string, email: string, password: string) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
    user: null,
    loading: true,
    login: async () => { },
    register: async () => { },
    logout: () => { },
});

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        const token = getToken();
        if (!token) {
            setLoading(false);
            return;
        }
        api
            .get<User>("/api/auth/me")
            .then(setUser)
            .catch(() => setToken(null))
            .finally(() => setLoading(false));
    }, []);

    const login = async (email: string, password: string) => {
        const res = await api.post<{ access_token: string }>("/api/auth/login", {
            email,
            password,
        });
        setToken(res.access_token);
        const me = await api.get<User>("/api/auth/me");
        setUser(me);
        router.push("/dashboard");
    };

    const register = async (name: string, email: string, password: string) => {
        await api.post("/api/auth/register", { name, email, password });
        await login(email, password);
    };

    const logout = () => {
        setToken(null);
        setUser(null);
        router.push("/");
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, register, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => useContext(AuthContext);
