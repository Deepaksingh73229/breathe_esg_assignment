'use client';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface DataPoint {
    month: string;
    scope_1: number;
    scope_2: number;
    scope_3: number;
    total: number;
}

interface Props { data: DataPoint[]; }

function formatMonth(m: string) {
    const [y, mo] = m.split('-');
    return new Date(Number(y), Number(mo) - 1).toLocaleDateString('en-US', { month: 'short' });
}
function fmtKg(n: number) {
    if (n >= 1e6) return `${(n / 1e6).toFixed(1)}Mt`;
    if (n >= 1e3) return `${(n / 1e3).toFixed(1)}t`;
    return `${n.toFixed(0)}kg`;
}

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; color: string }>; label?: string }) => {
    if (!active || !payload?.length) return null;
    return (
        <div style={{
            background: 'var(--color-navy-light)', border: '1px solid var(--color-border)',
            borderRadius: '12px', padding: '12px 16px', minWidth: '180px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
        }}>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--color-text-muted)', marginBottom: '8px', letterSpacing: '0.04em' }}>
                {label}
            </p>
            {payload.map(p => (
                <div key={p.name} style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', marginBottom: '4px' }}>
                    <span style={{ fontSize: '0.8rem', color: p.color }}>{p.name}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--color-text-primary)' }}>{fmtKg(p.value)}</span>
                </div>
            ))}
        </div>
    );
};

export default function EmissionsChart({ data }: Props) {
    const formatted = data.map(d => ({ ...d, month: formatMonth(d.month) }));

    return (
        <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={formatted} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                <defs>
                    <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ff6b35" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#ff6b35" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#4da6ff" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#4da6ff" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="g3" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#a78bfa" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#a78bfa" stopOpacity={0} />
                    </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,46,74,0.8)" vertical={false} />
                <XAxis dataKey="month" tick={{ fontFamily: 'DM Mono', fontSize: 11, fill: 'var(--color-text-muted)' }} axisLine={false} tickLine={false} />
                <YAxis tickFormatter={fmtKg} tick={{ fontFamily: 'DM Mono', fontSize: 11, fill: 'var(--color-text-muted)' }} axisLine={false} tickLine={false} width={50} />
                <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.05)', strokeWidth: 1 }} />
                <Area type="monotone" dataKey="scope_1" name="Scope 1" stroke="#ff6b35" strokeWidth={2} fill="url(#g1)" dot={false} activeDot={{ r: 4, fill: '#ff6b35' }} />
                <Area type="monotone" dataKey="scope_2" name="Scope 2" stroke="#4da6ff" strokeWidth={2} fill="url(#g2)" dot={false} activeDot={{ r: 4, fill: '#4da6ff' }} />
                <Area type="monotone" dataKey="scope_3" name="Scope 3" stroke="#a78bfa" strokeWidth={2} fill="url(#g3)" dot={false} activeDot={{ r: 4, fill: '#a78bfa' }} />
            </AreaChart>
        </ResponsiveContainer>
    );
}