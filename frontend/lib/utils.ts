import { clsx, type ClassValue } from 'clsx';

export function cn(...inputs: ClassValue[]) {
    return clsx(inputs);
}

export function formatCO2e(kg: number | string | null | undefined): string {
    if (kg === null || kg === undefined) return '—';
    const n = typeof kg === 'string' ? parseFloat(kg) : kg;
    if (isNaN(n)) return '—';
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)} t CO₂e`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(2)} t CO₂e`;
    return `${n.toFixed(1)} kg CO₂e`;
}

export function formatNumber(n: number | null | undefined, decimals = 0): string {
    if (n === null || n === undefined) return '—';
    return n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function formatDate(iso: string | null | undefined): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function formatDateTime(iso: string | null | undefined): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('en-US', {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    });
}

export const SCOPE_COLORS: Record<string, string> = {
    '1': '#ff6b35',
    '2': '#4da6ff',
    '3': '#a78bfa',
};

export const SCOPE_BG: Record<string, string> = {
    '1': 'rgba(255,107,53,0.12)',
    '2': 'rgba(77,166,255,0.12)',
    '3': 'rgba(167,139,250,0.12)',
};

export const STATUS_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
    pending: { color: '#fbbf24', bg: 'rgba(251,191,36,0.12)', label: 'Pending' },
    approved: { color: '#00e87a', bg: 'rgba(0,232,122,0.12)', label: 'Approved' },
    flagged: { color: '#f97316', bg: 'rgba(249,115,22,0.12)', label: 'Flagged' },
    rejected: { color: '#ef4444', bg: 'rgba(239,68,68,0.12)', label: 'Rejected' },
};

export const SOURCE_ICONS: Record<string, string> = {
    sap: '⚙',
    utility: '⚡',
    travel: '✈',
    manual: '✏',
};

export const SOURCE_LABELS: Record<string, string> = {
    sap: 'SAP',
    utility: 'Utility',
    travel: 'Travel',
    manual: 'Manual',
};