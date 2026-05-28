'use client';
import { ReactNode } from 'react';

interface StatCardProps {
    label: string;
    value: string;
    sub?: string;
    accent?: string;
    icon?: ReactNode;
    trend?: { value: number; label: string };
    delay?: number;
}

export default function StatCard({ label, value, sub, accent, icon, trend, delay = 0 }: StatCardProps) {
    return (
        <div className="card p-6 opacity-0 animate-fade-up"
            style={{
                animationDelay: `${delay}ms`,
                animationFillMode: 'forwards',
                position: 'relative',
                overflow: 'hidden',
            }}>
            {/* Top accent line */}
            {accent && (
                <div style={{
                    position: 'absolute', top: 0, left: '24px', right: '24px', height: '2px',
                    background: accent, borderRadius: '0 0 4px 4px', opacity: 0.8,
                }} />
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                    <p style={{
                        fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)',
                        letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '10px',
                    }}>{label}</p>
                    <p style={{
                        fontFamily: 'var(--font-display)', fontSize: '1.9rem', fontWeight: 700,
                        color: accent || 'var(--color-text-primary)', letterSpacing: '-0.02em',
                        lineHeight: 1, marginBottom: '6px',
                    }}>{value}</p>
                    {sub && (
                        <p style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>{sub}</p>
                    )}
                    {trend && (
                        <div style={{
                            display: 'inline-flex', alignItems: 'center', gap: '4px', marginTop: '8px',
                            padding: '2px 8px', borderRadius: '100px',
                            background: trend.value >= 0 ? 'rgba(0,232,122,0.1)' : 'rgba(239,68,68,0.1)',
                        }}>
                            <span style={{
                                fontSize: '0.7rem', fontFamily: 'var(--font-mono)',
                                color: trend.value >= 0 ? 'var(--color-emerald)' : '#ef4444',
                            }}>
                                {trend.value >= 0 ? '↑' : '↓'} {Math.abs(trend.value)}% {trend.label}
                            </span>
                        </div>
                    )}
                </div>
                {icon && (
                    <div style={{
                        width: '44px', height: '44px', borderRadius: '12px',
                        background: accent ? `${accent}15` : 'var(--color-slate)',
                        border: `1px solid ${accent ? `${accent}30` : 'var(--color-border)'}`,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        color: accent || 'var(--color-text-secondary)',
                        flexShrink: 0, marginLeft: '12px',
                    }}>
                        {icon}
                    </div>
                )}
            </div>
        </div>
    );
}