'use client';
import { useEffect, useState } from 'react';
import { api, IngestionHealth } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';

export default function IngestionHealthCard() {
    const [data, setData] = useState<IngestionHealth | null>(null);

    useEffect(() => {
        api.getIngestionHealth().then(setData).catch(console.error);
    }, []);

    const SOURCE_LABELS: Record<string, string> = { sap: 'SAP', utility: 'Utility', travel: 'Travel' };
    const STATUS_COLORS: Record<string, string> = {
        parsed: 'var(--color-emerald)',
        partial: 'var(--color-pending)',
        failed: '#ef4444',
        pending: 'var(--color-text-muted)',
    };

    return (
        <div className="card p-6 opacity-0 animate-fade-up" style={{ animationDelay: '520ms', animationFillMode: 'forwards' }}>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '4px' }}>
                Ingestion Health
            </h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '20px' }}>
                Data pipeline status by source
            </p>

            {!data ? (
                <div style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>Loading…</div>
            ) : (
                <>
                    {/* Source breakdown */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '20px' }}>
                        {(data.by_source || []).map(src => {
                            const rate = src.total > 0 ? Math.round((src.successful / src.total) * 100) : 0;
                            return (
                                <div key={src.source_type}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                                        <span style={{ fontSize: '0.8rem', color: 'var(--color-text-primary)' }}>
                                            {SOURCE_LABELS[src.source_type] || src.source_type}
                                        </span>
                                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: rate > 90 ? 'var(--color-emerald)' : rate > 70 ? 'var(--color-pending)' : '#ef4444' }}>
                                            {rate}%
                                        </span>
                                    </div>
                                    <div style={{ height: '4px', borderRadius: '100px', background: 'var(--color-slate)' }}>
                                        <div style={{
                                            height: '100%', borderRadius: '100px', width: `${rate}%`,
                                            background: rate > 90 ? 'var(--color-emerald)' : rate > 70 ? 'var(--color-pending)' : '#ef4444',
                                            transition: 'width 1s cubic-bezier(0.16,1,0.3,1)',
                                        }} />
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {/* Recent runs */}
                    <div>
                        <p style={{ fontSize: '0.65rem', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: '10px' }}>
                            Recent Runs
                        </p>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {(data.recent_runs || []).slice(0, 4).map(run => (
                                <div key={run.id} style={{
                                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                    padding: '8px 12px', borderRadius: '8px', background: 'var(--color-slate)',
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: STATUS_COLORS[run.status] || 'var(--color-text-muted)', display: 'inline-block' }} />
                                        <span style={{ fontSize: '0.78rem', color: 'var(--color-text-primary)' }}>
                                            {run.source_type_display || run.source_type}
                                        </span>
                                    </div>
                                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--color-text-muted)' }}>
                                        {formatDateTime(run.created_at)}
                                    </span>
                                </div>
                            ))}
                            {(!data.recent_runs || data.recent_runs.length === 0) && (
                                <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', textAlign: 'center', padding: '16px' }}>No ingestion runs yet</p>
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}