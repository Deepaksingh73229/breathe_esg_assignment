// API client — communicates with the Django REST backend

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

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = getAuthToken();
    const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
    const headers: Record<string, string> = {
        ...(!isFormData ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Token ${token}` } : {}),
        ...(options.headers as Record<string, string> || {}),
    };

    try {
        const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

        // Handle unauthorized centrally: clear token and redirect to root/login
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

export const api = {
    // Auth
    login: (username: string, password: string) =>
        request<{ token: string }>('/auth/login/', {
            method: 'POST',
            body: JSON.stringify({ username, password }),
        }),

    // Dashboard
    getDashboardSummary: () => request<DashboardSummary>('/dashboard/summary/'),
    getDashboardTrends: (months = 6) =>
        request<TrendData>(`/dashboard/trends/?months=${months}`),
    getIngestionHealth: () => request<IngestionHealth>('/dashboard/ingestion_health/'),
    getReviewQueue: (params?: Record<string, string>) => {
        const qs = params ? '?' + new URLSearchParams(params).toString() : '';
        return request<ReviewQueueResponse>(`/dashboard/review_queue/${qs}`);
    },

    // Activities
    getActivities: (params?: Record<string, string>) => {
        const qs = params ? '?' + new URLSearchParams(params).toString() : '';
        return request<PaginatedResponse<ActivityRecord>>(`/activities/${qs}`);
    },
    getActivity: (id: string) => request<ActivityRecord>(`/activities/${id}/`),
    approveActivity: (id: string, notes?: string) =>
        request(`/activities/${id}/approve/`, {
            method: 'POST',
            body: JSON.stringify({ notes: notes || '' }),
        }),
    rejectActivity: (id: string, notes?: string) =>
        request(`/activities/${id}/reject/`, {
            method: 'POST',
            body: JSON.stringify({ notes: notes || '' }),
        }),
    flagActivity: (id: string, notes?: string) =>
        request(`/activities/${id}/flag/`, {
            method: 'POST',
            body: JSON.stringify({ notes: notes || '' }),
        }),
    bulkReview: (ids: string[], action: string, notes?: string) =>
        request('/activities/bulk_review/', {
            method: 'POST',
            body: JSON.stringify({ ids, action, notes: notes || '' }),
        }),
    getAuditTrail: (id: string) => request(`/activities/${id}/audit_trail/`),

    // Ingestion
    uploadFile: (formData: FormData) =>
        request<IngestionResult>('/ingestion/', { method: 'POST', body: formData }),
    getIngestionRuns: () => request<PaginatedResponse<IngestionRun>>('/ingestion/'),
    getIngestionRun: (id: string) => request<IngestionRun>(`/ingestion/${id}/`),

    // Factors
    getFactors: (params?: Record<string, string>) => {
        const qs = params ? '?' + new URLSearchParams(params).toString() : '';
        return request<PaginatedResponse<EmissionFactor>>(`/factors/${qs}`);
    },

    // Facilities
    getFacilities: () => request<PaginatedResponse<Facility>>('/facilities/'),

    // Audit
    getAuditLogs: (params?: Record<string, string>) => {
        const qs = params ? '?' + new URLSearchParams(params).toString() : '';
        return request<PaginatedResponse<AuditEntry>>(`/audit/${qs}`);
    },
};

// ── Types ─────────────────────────────────────────────────────────────────────

export interface DashboardSummary {
    scope_totals: Record<string, { total_co2e_kg: number; record_count: number }>;
    review_queue: Record<string, { count: number; total_co2e_kg: number }>;
    recent_ingestions: Array<{ source_type: string; status: string; count: number }>;
    facility_count: number;
    organization_count: number;
}

export interface TrendData {
    months: number;
    data: Array<{
        month: string;
        scope_1: number;
        scope_2: number;
        scope_3: number;
        total: number;
    }>;
}

export interface IngestionHealth {
    by_source: Array<{
        source_type: string;
        total: number;
        successful: number;
        failed: number;
        partial: number;
    }>;
    recent_runs: IngestionRun[];
}

export interface ReviewQueueResponse {
    count: number;
    page: number;
    page_size: number;
    results: ActivityRecord[];
}

export interface ActivityRecord {
    id: string;
    organization: string;
    facility: string | null;
    facility_name: string;
    source_system: string;
    source_system_display: string;
    source_identifier: string;
    scope: string;
    scope_display: string;
    activity_type: string;
    activity_type_display: string;
    activity_amount: string;
    activity_unit: string;
    co2e_kg: string | null;
    period_start: string;
    period_end: string;
    review_status: string;
    review_status_display: string;
    is_estimated: boolean;
    is_edited: boolean;
    created_at: string;
    fuel_type?: string;
    distance_band?: string;
    travel_class?: string;
    origin_location?: string;
    destination_location?: string;
    co2e_calculation_audit?: Record<string, unknown>;
    parse_errors?: string[];
}

export interface IngestionRun {
    id: string;
    organization: string;
    source_type: string;
    source_type_display: string;
    status: string;
    status_display: string;
    total_rows: number | null;
    valid_rows: number | null;
    invalid_rows: number | null;
    suspicious_rows: number | null;
    error_summary: Record<string, number>;
    period_start: string | null;
    period_end: string | null;
    checksum: string;
    created_at: string;
}

export interface IngestionResult {
    id: string;
    status: string;
    pipeline_result: {
        status: string;
        total_rows: number;
        valid_rows: number;
        invalid_rows: number;
        suspicious_rows: number;
    };
}

export interface EmissionFactor {
    id: string;
    name: string;
    source: string;
    source_version: string;
    activity_type: string;
    region: string;
    fuel_type: string;
    co2e_kg_per_unit: string;
    unit: string;
    effective_from: string;
    is_active: boolean;
}

export interface Facility {
    id: string;
    name: string;
    sap_plant_code: string;
    city: string;
    country: string;
    facility_type: string;
    egrid_subregion_effective: string;
}

export interface AuditEntry {
    id: string;
    table_name: string;
    record_id: string | null;
    action: string;
    action_display: string;
    changed_fields: Record<string, unknown>;
    performed_by_email: string;
    performed_by_name: string;
    ip_address: string | null;
    created_at: string;
}

export interface PaginatedResponse<T> {
    count: number;
    next: string | null;
    previous: string | null;
    results: T[];
}