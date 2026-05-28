'use client';
import { useEffect, useState } from 'react';
import { api, AuditEntry } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';

const ACTION_COLORS: Record<string, string> = {
    create: '#00e87a',
    update: '#4da6ff',
    delete: '#ef4444',
    review_transition: '#a78bfa',
    bulk_approve: '#00e87a',
    bulk_reject: '#ef4444',
    bulk_flag: '#f97316',
    ingestion: '#fbbf24',
    recalculation: '#4da6ff',
    login: '#8899b8',
    logout: '#8899b8',
};

export default function AuditPage() {
    const [logs, setLogs] = useState<AuditEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState<string | null>(null);

    useEffect(() => {
        api.getAuditLogs({ page_size: '50' })
            .then(d => setLogs(d.results || []))
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    return (
        <div style={{ padding: '32px 36px', maxWidth: '1100px' }}>
            {/* Header */}
            <div style={{ marginBottom: '32px' }}>
                <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--color-text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '6px' }}>Compliance & Security</p>
                <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 700, color: 'var(--color-text-primary)', letterSpacing: '-0.03em', marginBottom: '8px' }}>
                    Audit <span style={{ color: 'var(--color-emerald)' }}>Trail</span>
                </h1>
                <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>
                    Append-only log of every significant action. Records are never modified or deleted.
                </p>
            </div>

            {/* Stats banner */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '24px' }}>
                {[
                    { label: 'Total Entries', value: logs.length, color: 'var(--color-text-primary)' },
                    { label: 'Review Actions', value: logs.filter(l => l.action === 'review_transition').length, color: '#a78bfa' },
                    { label: 'Edits', value: logs.filter(l => l.action === 'update').length, color: '#4da6ff' },
                    { label: 'Ingestions', value: logs.filter(l => l.action === 'ingestion').length, color: '#fbbf24' },
                ].map(s => (
                    <div key={s.label} className="card" style={{ padding: '16px 20px' }}>
                        <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', fontWeight: 700, color: s.color, lineHeight: 1, marginBottom: '4px' }}>{s.value}</div>
                        <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{s.label}</div>
                    </div>
                ))}
            </div>

            {/* Timeline */}
            <div className="card" style={{ overflow: 'hidden' }}>
                {loading ? (
                    <div style={{ padding: '60px', textAlign: 'center', color: 'var(--color-text-muted)' }}>Loading audit log…</div>
                ) : logs.length === 0 ? (
                    <div style={{ padding: '60px', textAlign: 'center' }}>
                        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>No audit entries yet. Actions will appear here.</p>
                    </div>
                ) : (
                    <div style={{ position: 'relative' }}>
                        {/* Timeline line */}
                        <div style={{ position: 'absolute', left: '28px', top: 0, bottom: 0, width: '1px', background: 'var(--color-border)' }} />

                        {logs.map((log, i) => {
                            const color = ACTION_COLORS[log.action] || '#8899b8';
                            const isExpanded = expanded === log.id;
                            return (
                                <div key={log.id} style={{
                                    padding: '16px 20px 16px 56px',
                                    borderBottom: i < logs.length - 1 ? '1px solid rgba(30,46,74,0.4)' : 'none',
                                    position: 'relative',
                                    cursor: 'pointer',
                                    transition: 'background 0.15s',
                                }}
                                    onClick={() => setExpanded(isExpanded ? null : log.id)}
                                    onMouseEnter={e => (e.currentTarget as HTMLDivElement).style.background = 'rgba(26,39,64,0.4)'}
                                    onMouseLeave={e => (e.currentTarget as HTMLDivElement).style.background = 'transparent'}>

                                    {/* Timeline dot */}
                                    <div style={{
                                        position: 'absolute', left: '22px', top: '22px',
                                        width: '12px', height: '12px', borderRadius: '50%',
                                        background: color, boxShadow: `0 0 8px ${color}60`,
                                        border: '2px solid var(--color-obsidian)',
                                    }} />

                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px' }}>
                                        <div style={{ flex: 1, minWidth: 0 }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
                                                <span className="badge" style={{ background: `${color}15`, color, border: `1px solid ${color}30`, fontSize: '0.68rem' }}>
                                                    {log.action_display || log.action}
                                                </span>
                                                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                    {log.table_name}
                                                    {log.record_id && ` · ${log.record_id.slice(0, 8)}…`}
                                                </span>
                                            </div>
                                            <div style={{ fontSize: '0.82rem', color: 'var(--color-text-secondary)' }}>
                                                <span style={{ color: 'var(--color-text-primary)', fontWeight: 500 }}>{log.performed_by_name || log.performed_by_email || 'System'}</span>
                                                {log.ip_address && <span style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.72rem', marginLeft: '8px' }}>from {log.ip_address}</span>}
                                            </div>
                                        </div>
                                        <div style={{ textAlign: 'right', flexShrink: 0 }}>
                                            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                                                {formatDateTime(log.created_at)}
                                            </div>
                                            <div style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                                                {isExpanded ? '▲ collapse' : '▼ details'}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Expanded payload */}
                                    {isExpanded && (
                                        <div className="animate-fade-in" style={{ marginTop: '12px', padding: '12px 16px', borderRadius: '10px', background: 'var(--color-slate)', border: '1px solid var(--color-border)' }}>
                                            <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--color-text-muted)', marginBottom: '6px', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                                                Changed Fields
                                            </p>
                                            <pre style={{
                                                fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-text-secondary)',
                                                margin: 0, overflowX: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                                            }}>
                                                {JSON.stringify(log.changed_fields, null, 2)}
                                            </pre>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Compliance note */}
            <div style={{ marginTop: '20px', padding: '16px 20px', borderRadius: '12px', background: 'rgba(0,232,122,0.05)', border: '1px solid rgba(0,232,122,0.15)' }}>
                <p style={{ fontSize: '0.78rem', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
                    <span style={{ color: 'var(--color-emerald)', fontWeight: 600 }}>Audit integrity:</span>{' '}
                    This log is append-only at the database level. Every mutation to business data creates an immutable entry recording who, what, when, and from where. Entries cannot be modified or deleted — an auditor can use this log to reconstruct the full history of any ActivityRecord.
                </p>
            </div>
        </div>
    );
}