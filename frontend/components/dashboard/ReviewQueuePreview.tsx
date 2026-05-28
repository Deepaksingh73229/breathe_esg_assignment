'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api, ActivityRecord } from '@/lib/api';
import { formatCO2e, formatDate } from '@/lib/utils';
import { StatusBadge, ScopeBadge, SourceBadge } from '@/components/ui/Badge';

export default function ReviewQueuePreview() {
    const [records, setRecords] = useState<ActivityRecord[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.getReviewQueue({ status: 'pending,flagged', page_size: '8' })
            .then(d => { setRecords(d.results); setTotal(d.count); })
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    return (
        <div className="card" style={{ overflow: 'hidden' }}>
            <div style={{ padding: '20px 24px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--color-border)' }}>
                <div>
                    <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '2px' }}>
                        Review Queue
                    </h2>
                    <p style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
                        {total} records awaiting analyst sign-off
                    </p>
                </div>
                <Link href="/review" style={{ textDecoration: 'none' }}>
                    <button className="btn-ghost" style={{ fontSize: '0.8rem', padding: '7px 14px' }}>
                        View All →
                    </button>
                </Link>
            </div>

            {loading ? (
                <div style={{ padding: '24px', color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>Loading…</div>
            ) : records.length === 0 ? (
                <div style={{ padding: '40px', textAlign: 'center' }}>
                    <div style={{ fontSize: '2rem', marginBottom: '8px' }}>✓</div>
                    <p style={{ color: 'var(--color-emerald)', fontWeight: 600, marginBottom: '4px' }}>Queue is clear</p>
                    <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>No records pending review</p>
                </div>
            ) : (
                <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                        <tr>
                            <th style={{ textAlign: 'left' }}>Source</th>
                            <th style={{ textAlign: 'left' }}>Facility</th>
                            <th style={{ textAlign: 'left' }}>Type</th>
                            <th style={{ textAlign: 'left' }}>Period</th>
                            <th style={{ textAlign: 'right' }}>CO₂e</th>
                            <th style={{ textAlign: 'left' }}>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {records.map(r => (
                            <tr key={r.id} style={{ cursor: 'pointer' }} onClick={() => window.open(`/review/${r.id}`, '_self')}>
                                <td>
                                    <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                                        <SourceBadge source={r.source_system} />
                                        <ScopeBadge scope={r.scope} />
                                    </div>
                                </td>
                                <td style={{ color: 'var(--color-text-secondary)', maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    {r.facility_name || 'Unassigned'}
                                </td>
                                <td style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem', maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    {r.activity_type_display}
                                </td>
                                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                                    {formatDate(r.period_start)}
                                </td>
                                <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: r.co2e_kg ? 'var(--color-text-primary)' : 'var(--color-text-muted)' }}>
                                    {r.co2e_kg ? formatCO2e(parseFloat(r.co2e_kg)) : '—'}
                                </td>
                                <td><StatusBadge status={r.review_status} size="sm" /></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    );
}