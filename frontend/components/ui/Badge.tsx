import { STATUS_CONFIG } from '@/lib/utils';

interface BadgeProps {
    status: string;
    size?: 'sm' | 'md';
}

export function StatusBadge({ status, size = 'md' }: BadgeProps) {
    const cfg = STATUS_CONFIG[status] || { color: '#8899b8', bg: 'rgba(136,153,184,0.1)', label: status };
    return (
        <span className="badge" style={{
            background: cfg.bg, color: cfg.color,
            border: `1px solid ${cfg.color}30`,
            fontSize: size === 'sm' ? '0.62rem' : '0.7rem',
            padding: size === 'sm' ? '2px 8px' : '3px 10px',
        }}>
            <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: cfg.color, display: 'inline-block', flexShrink: 0 }} />
            {cfg.label}
        </span>
    );
}

interface ScopeBadgeProps { scope: string; }
const SCOPE_CFG: Record<string, { color: string; bg: string }> = {
    '1': { color: '#ff6b35', bg: 'rgba(255,107,53,0.12)' },
    '2': { color: '#4da6ff', bg: 'rgba(77,166,255,0.12)' },
    '3': { color: '#a78bfa', bg: 'rgba(167,139,250,0.12)' },
};
export function ScopeBadge({ scope }: ScopeBadgeProps) {
    const cfg = SCOPE_CFG[scope] || { color: '#8899b8', bg: 'rgba(136,153,184,0.1)' };
    return (
        <span className="badge" style={{ background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.color}30`, fontSize: '0.7rem' }}>
            S{scope}
        </span>
    );
}

interface SourceBadgeProps { source: string; }
const SOURCE_CFG: Record<string, { color: string; bg: string; icon: string }> = {
    sap: { color: '#fbbf24', bg: 'rgba(251,191,36,0.1)', icon: '⚙' },
    utility: { color: '#4da6ff', bg: 'rgba(77,166,255,0.1)', icon: '⚡' },
    travel: { color: '#a78bfa', bg: 'rgba(167,139,250,0.1)', icon: '✈' },
    manual: { color: '#8899b8', bg: 'rgba(136,153,184,0.1)', icon: '✏' },
};
export function SourceBadge({ source }: SourceBadgeProps) {
    const cfg = SOURCE_CFG[source] || SOURCE_CFG.manual;
    return (
        <span className="badge" style={{ background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.color}30`, fontSize: '0.7rem' }}>
            {cfg.icon} {source.toUpperCase()}
        </span>
    );
}