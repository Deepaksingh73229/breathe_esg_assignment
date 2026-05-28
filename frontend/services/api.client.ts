// Base API client for the Breathe ESG frontend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export function setAuthToken(token: string) {
    if (typeof window !== 'undefined') localStorage.setItem('breathe_token', token);
}

export function getAuthToken(): string | null {
    if (typeof window !== 'undefined') return localStorage.getItem('breathe_token');
    return null;
}

export function clearAuthToken() {
    if (typeof window !== 'undefined') localStorage.removeItem('breathe_token');
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = getAuthToken();
    const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
    const headers: Record<string, string> = {
        ...(!isFormData ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Token ${token}` } : {}),
        ...(options.headers as Record<string, string> || {}),
    };

    try {
        const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

        if (res.status === 401) {
            if (typeof window !== 'undefined') {
                clearAuthToken();
                window.location.href = '/';
            }
            throw new Error('Unauthorized');
        }

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            const msg = err?.error?.message || err?.detail || `HTTP ${res.status}`;
            throw new Error(msg);
        }

        if (res.status === 204) return {} as T;

        return await res.json().catch(() => ({} as T));
    } catch (e: unknown) {
        const message =
            e instanceof Error
                ? e.message
                : typeof e === 'string'
                ? e
                : JSON.stringify(e ?? 'An unexpected error occurred.');
        throw new Error(message);
    }
}
