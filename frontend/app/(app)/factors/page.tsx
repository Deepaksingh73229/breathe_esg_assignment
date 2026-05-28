'use client';
import { useEffect, useState } from 'react';
import { api, EmissionFactor } from '@/lib/api';

const ACTIVITY_TYPES = [
    { value: '', label: 'All Types' },
    { value: 'purchased_electricity', label: 'Electricity (Scope 2)' },
    { value: 'stationary_fuel', label: 'Stationary Fuel (Scope 1)' },
    { value: 'business_travel_flight', label: 'Flight (Scope 3)' },
    { value: 'business_travel_rail', label: 'Rail (Scope 3)' },
    { value: 'business_travel_car', label: 'Car (Scope 3)' },
    { value: 'business_travel_hotel', label: 'Hotel (Scope 3)' },
];

const SOURCE_COLORS: Record<string, string> = {
    epa_egrid: '#4da6ff',
    defra: '#a78bfa',
    ipcc: '#00e87a',
    epa: '#4da6ff',
    custom: '#fbbf24',
};

export default function FactorsPage() {
    const [factors, setFactors] = useState<EmissionFactor[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [activityType, setActivityType] = useState('');
    const [search, setSearch] = useState('');

    useEffect(() => {
        setLoading(true);
        const params: Record<string, string> = { page_size: '50' };
        if (activityType) params.activity_type = activityType;
        api.getFactors(params)
            .then(d => { setFactors(d.results); setTotal(d.count); })
            .catch(console.error)
            .finally(() => setLoading(false));
    }, [activityType]);

    const filtered = search
        ? factors.filter(f =>
            f.name.toLowerCase().includes(search.toLowerCase()) ||
            f.region.toLowerCase().includes(search.toLowerCase()) ||
            f.source_version.toLowerCase().includes(search.toLowerCase())
        )
        : factors;

    return (
        <div style={{ padding: '32px 36px', maxWidth: '1200px' }}>
            {/* Header */}
            <div style={{ marginBottom: '32px' }}>
                <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--color-text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '6px' }}>Carbon Accounting</p>
                <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 700, color: 'var(--color-text-primary)', letterSpacing: '-0.03em', marginBottom: '8px' }}>
                    Emission <span style={{ color: 'var(--color-emerald)' }}>Factors</span>
                </h1>
                <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>
                    {total} active versioned factors — eGRID2022 · DEFRA 2025 · IPCC 2006
                </p>
            </div>

            {/* Source legend */}
            <div style={{ display: 'flex', gap: '16px', marginBottom: '24px', flexWrap: 'wrap' }}>
                {[
                    { key: 'epa_egrid', label: 'EPA eGRID2022', desc: 'US electricity (26 subregions)' },
                    { key: 'defra', label: 'DEFRA 2025', desc: 'UK travel & fuel' },
                    { key: 'ipcc', label: 'IPCC 2006', desc: 'Global fuel combustion' },
                ].map(s => (
                    <div key={s.key} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 16px', borderRadius: '10px', background: 'var(--color-navy)', border: '1px solid var(--color-border)' }}>
                        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: SOURCE_COLORS[s.key], flexShrink: 0, boxShadow: `0 0 6px ${SOURCE_COLORS[s.key]}60` }} />
                        <div>
                            <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>{s.label}</div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>{s.desc}</div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Filters */}
            <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
                <input
                    className="input-base"
                    placeholder="Search by name, region, version…"
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    style={{ maxWidth: '320px' }}
                />
                <select className="input-base" value={activityType} onChange={e => setActivityType(e.target.value)} style={{ width: 'auto' }}>
                    {ACTIVITY_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
            </div>

            {/* Factors table */}
            <div className="card" style={{ overflow: 'hidden' }}>
                {loading ? (
                    <div style={{ padding: '60px', textAlign: 'center', color: 'var(--color-text-muted)' }}>Loading factors…</div>
                ) : (
                    <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr>
                                <th style={{ textAlign: 'left' }}>Factor Name</th>
                                <th style={{ textAlign: 'left' }}>Source</th>
                                <th style={{ textAlign: 'left' }}>Region</th>
                                <th style={{ textAlign: 'left' }}>Activity Type</th>
                                <th style={{ textAlign: 'right' }}>kg CO₂e / unit</th>
                                <th style={{ textAlign: 'left' }}>Unit</th>
                                <th style={{ textAlign: 'left' }}>Valid From</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.map(f => (
                                <tr key={f.id}>
                                    <td>
                                        <div style={{ fontWeight: 500, fontSize: '0.82rem', color: 'var(--color-text-primary)', maxWidth: '260px' }}>
                                            {f.name}
                                        </div>
                                    </td>
                                    <td>
                                        <span className="badge" style={{
                                            background: `${SOURCE_COLORS[f.source] || '#8899b8'}15`,
                                            color: SOURCE_COLORS[f.source] || '#8899b8',
                                            border: `1px solid ${SOURCE_COLORS[f.source] || '#8899b8'}30`,
                                            fontSize: '0.68rem',
                                        }}>
                                            {f.source_version}
                                        </span>
                                    </td>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--color-text-secondary)' }}>
                                        {f.region}
                                    </td>
                                    <td style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {f.activity_type.replace(/_/g, ' ')}
                                    </td>
                                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', fontWeight: 600, color: 'var(--color-emerald)' }}>
                                        {parseFloat(f.co2e_kg_per_unit).toFixed(5)}
                                    </td>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                                        /{f.unit}
                                    </td>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                                        {f.effective_from}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Why versioned factors matter */}
            <div style={{ marginTop: '24px', padding: '20px 24px', borderRadius: '14px', background: 'var(--color-navy)', border: '1px solid var(--color-border)' }}>
                <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                    <span style={{ fontSize: '1.2rem' }}>💡</span>
                    <div>
                        <p style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '4px' }}>Why versioned factors?</p>
                        <p style={{ fontSize: '0.78rem', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
                            EPA releases eGRID data every ~2 years; DEFRA updates annually. Factors are time-bounded (effective_from / effective_to) so that historical ActivityRecords always use the factor vintage that was active when the activity occurred — ensuring audit defensibility across reporting years.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}