'use client';
import { useEffect, useState } from 'react';
import { api, DashboardSummary, TrendData } from '@/lib/api';
import { formatCO2e, formatNumber } from '@/lib/utils';
import StatCard from '@/components/ui/StatCard';
import EmissionsChart from '@/components/charts/EmissionsChart';
import ReviewQueuePreview from '@/components/dashboard/ReviewQueuePreview';
import IngestionHealthCard from '@/components/dashboard/IngestionHealthCard';

export default function DashboardPage() {
    const [summary, setSummary] = useState<DashboardSummary | null>(null);
    const [trends, setTrends] = useState<TrendData | null>(null);
    const [loading, setLoading] = useState(true);
    const [now] = useState(() => new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }));

    useEffect(() => {
        Promise.all([api.getDashboardSummary(), api.getDashboardTrends(6)])
            .then(([s, t]) => { setSummary(s); setTrends(t); })
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    const totalApproved = summary
        ? Object.values(summary.scope_totals).reduce((a, b) => a + b.total_co2e_kg, 0)
        : 0;

    const pendingCount = summary?.review_queue?.pending?.count ?? 0;
    const flaggedCount = summary?.review_queue?.flagged?.count ?? 0;

    return (
        <div style={{ padding: '32px 36px', maxWidth: '1400px' }}>

            {/* Header */}
            <div style={{ marginBottom: '36px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--color-text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '6px' }}>
                        {now}
                    </p>
                    <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 700, color: 'var(--color-text-primary)', letterSpacing: '-0.03em', lineHeight: 1 }}>
                        Emissions <span style={{ color: 'var(--color-emerald)' }}>Overview</span>
                    </h1>
                    <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem', marginTop: '6px' }}>
                        GHG Protocol — Scope 1, 2 & 3 consolidated view
                    </p>
                </div>

                {/* Live indicator */}
                <div style={{
                    display: 'flex', alignItems: 'center', gap: '8px',
                    padding: '8px 16px', borderRadius: '100px',
                    background: 'rgba(0,232,122,0.08)', border: '1px solid rgba(0,232,122,0.2)',
                }}>
                    <span className="animate-pulse-dot" style={{ width: '7px', height: '7px', borderRadius: '50%', background: 'var(--color-emerald)', display: 'inline-block' }} />
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--color-emerald)', letterSpacing: '0.05em' }}>
                        LIVE DATA
                    </span>
                </div>
            </div>

            {loading ? <LoadingSkeleton /> : (
                <>
                    {/* Top stats row */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
                        <StatCard
                            label="Total CO₂e (Approved)"
                            value={formatCO2e(totalApproved)}
                            sub="All scopes, approved records"
                            accent="var(--color-emerald)"
                            icon={<LeafIcon />}
                            delay={0}
                        />
                        <StatCard
                            label="Scope 1 — Direct"
                            value={formatCO2e(summary?.scope_totals?.['1']?.total_co2e_kg ?? 0)}
                            sub={`${formatNumber(summary?.scope_totals?.['1']?.record_count ?? 0)} records`}
                            accent="var(--color-scope1)"
                            icon={<FlameIcon />}
                            delay={80}
                        />
                        <StatCard
                            label="Scope 2 — Electricity"
                            value={formatCO2e(summary?.scope_totals?.['2']?.total_co2e_kg ?? 0)}
                            sub={`${formatNumber(summary?.scope_totals?.['2']?.record_count ?? 0)} records`}
                            accent="var(--color-scope2)"
                            icon={<BoltIcon />}
                            delay={160}
                        />
                        <StatCard
                            label="Scope 3 — Value Chain"
                            value={formatCO2e(summary?.scope_totals?.['3']?.total_co2e_kg ?? 0)}
                            sub={`${formatNumber(summary?.scope_totals?.['3']?.record_count ?? 0)} records`}
                            accent="var(--color-scope3)"
                            icon={<GlobeIcon />}
                            delay={240}
                        />
                    </div>

                    {/* Second stats row */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '24px' }}>
                        <StatCard
                            label="Pending Review"
                            value={formatNumber(pendingCount)}
                            sub="Records awaiting analyst sign-off"
                            accent="var(--color-pending)"
                            icon={<ClockIcon />}
                            delay={300}
                        />
                        <StatCard
                            label="Flagged for Attention"
                            value={formatNumber(flaggedCount)}
                            sub="Potential data quality issues"
                            accent="var(--color-flagged)"
                            icon={<FlagIcon />}
                            delay={360}
                        />
                        <StatCard
                            label="Facilities"
                            value={formatNumber(summary?.facility_count ?? 0)}
                            sub="Active monitored locations"
                            accent="#4da6ff"
                            icon={<BuildingIcon />}
                            delay={420}
                        />
                    </div>

                    {/* Charts row */}
                    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '16px', marginBottom: '24px' }}>
                        <div className="card p-6 opacity-0 animate-fade-up" style={{ animationDelay: '480ms', animationFillMode: 'forwards' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                                <div>
                                    <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '4px' }}>
                                        Emissions Trend
                                    </h2>
                                    <p style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
                                        6-month approved CO₂e by scope
                                    </p>
                                </div>
                                <div style={{ display: 'flex', gap: '16px' }}>
                                    {[['Scope 1', 'var(--color-scope1)'], ['Scope 2', 'var(--color-scope2)'], ['Scope 3', 'var(--color-scope3)']].map(([l, c]) => (
                                        <div key={l} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            <div style={{ width: '8px', height: '8px', borderRadius: '2px', background: c }} />
                                            <span style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)' }}>{l}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            {trends && <EmissionsChart data={trends.data} />}
                        </div>

                        <IngestionHealthCard />
                    </div>

                    {/* Review queue preview */}
                    <div className="opacity-0 animate-fade-up" style={{ animationDelay: '560ms', animationFillMode: 'forwards' }}>
                        <ReviewQueuePreview />
                    </div>
                </>
            )}
        </div>
    );
}

function LoadingSkeleton() {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {[1, 2, 3].map(i => (
                <div key={i} style={{
                    height: '120px', borderRadius: '16px',
                    background: 'linear-gradient(90deg, var(--color-navy) 25%, var(--color-navy-light) 50%, var(--color-navy) 75%)',
                    backgroundSize: '200% 100%',
                    animation: 'shimmer 1.5s infinite',
                }} />
            ))}
        </div>
    );
}

// ── Icon set ──────────────────────────────────────────────────────────────────
const ico = (path: string, size = 20) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d={path} />
    </svg>
);
function LeafIcon() { return ico("M5 8a7 7 0 1 1 14 0c0 5-7 11-7 11S5 13 5 8z M12 8a2 2 0 1 0 4 0 2 2 0 0 0-4 0"); }
function FlameIcon() { return ico("M12 2c0 6-8 6-8 12a8 8 0 0 0 16 0c0-4-2-6-4-8 0 4-3 5-3 8"); }
function BoltIcon() { return ico("M13 2L3 14h9l-1 8 10-12h-9l1-8z"); }
function GlobeIcon() { return ico("M12 2a10 10 0 1 0 0 20A10 10 0 0 0 12 2zM2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"); }
function ClockIcon() { return ico("M12 6v6l4 2 M12 2a10 10 0 1 0 0 20A10 10 0 0 0 12 2z"); }
function FlagIcon() { return ico("M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z M4 22v-7"); }
function BuildingIcon() { return ico("M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z M9 22V12h6v10"); }