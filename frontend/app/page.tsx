'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, setAuthToken } from '@/lib/api';
import Image from 'next/image';

import login from "@/public/login.png"

export default function LoginPage() {
    const router = useRouter();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    async function handleLogin(e: React.FormEvent) {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            const { token } = await api.login(username, password);
            setAuthToken(token);
            router.push('/dashboard');
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Login failed');
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="min-h-screen relative overflow-hidden flex items-center justify-center"
            style={{ background: 'var(--color-obsidian)' }}>
            <div className="absolute inset-0 grid-texture opacity-40" />
            <div className="absolute -bottom-40 -left-40 w-[600px] h-[600px] rounded-full pointer-events-none"
                style={{ background: 'radial-gradient(circle, rgba(0,232,122,0.07) 0%, transparent 70%)' }} />
            <div className="absolute -top-40 -right-40 w-[500px] h-[500px] rounded-full pointer-events-none"
                style={{ background: 'radial-gradient(circle, rgba(77,166,255,0.06) 0%, transparent 70%)' }} />

            {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map((i) => (
                <div key={i} className="absolute rounded-full pointer-events-none"
                    style={{
                        width: `${2 + (i % 3)}px`, height: `${2 + (i % 3)}px`,
                        background: i % 3 === 0 ? 'var(--color-emerald)' : i % 3 === 1 ? 'var(--color-scope2)' : 'var(--color-scope3)',
                        left: `${8 + i * 8}%`, top: `${10 + (i * 7) % 80}%`,
                        opacity: 0.3 + (i % 4) * 0.1,
                        animation: `pulse-dot ${2 + i * 0.3}s ease-in-out infinite`,
                        animationDelay: `${i * 0.2}s`,
                    }} />
            ))}

            <div className="relative z-10 w-full max-w-md px-6 animate-fade-up">
                <div className="text-center mb-10">
                    <div className="inline-flex items-center gap-3 mb-6">
                        <div className="relative">
                            <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                                style={{ background: 'var(--color-emerald)', boxShadow: '0 0 24px rgba(0,232,122,0.4)' }}>
                                <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                                    <circle cx="12" cy="12" r="9" fill="#080c14" opacity="0.3" />
                                    <path d="M7 13l3 3 7-7" stroke="#080c14" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                            </div>
                        </div>

                        <span style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 800, color: 'var(--color-text-primary)', letterSpacing: '-0.02em' }}>
                            breathe<span style={{ color: 'var(--color-emerald)' }}>ESG</span>
                        </span>
                    </div>
                    <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 700, color: 'var(--color-text-primary)', letterSpacing: '-0.03em', lineHeight: 1.1, marginBottom: '8px' }}>
                        Carbon Intelligence<br />
                        <span style={{ color: 'var(--color-emerald)', filter: 'drop-shadow(0 0 12px rgba(0,232,122,0.4))' }}>Platform</span>
                    </h1>

                    <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>Scope 1 · 2 · 3 · GHG Protocol · Auditor-Ready</p>
                </div>

                {/* Image placeholder */}
                <Image
                    src={login}
                    alt="Carbon emissions data visualization"
                    width={800}
                    height={160}
                    className="rounded-2xl"
                    priority
                />

                <div className="card p-8" style={{ boxShadow: '0 24px 80px rgba(0,0,0,0.4)' }}>
                    <form onSubmit={handleLogin} className="flex flex-col gap-5">
                        <div>
                            <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--color-text-secondary)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Username</label>
                            <input className="input-base" type="text" value={username} onChange={e => setUsername(e.target.value)} placeholder="analyst@breatheesg.com" required />
                        </div>

                        <div>
                            <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--color-text-secondary)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Password</label>
                            <input className="input-base" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" required />
                        </div>

                        {error && (
                            <div className="rounded-lg px-4 py-3" style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)' }}>
                                <span style={{ color: '#ef4444', fontSize: '0.875rem' }}>{error}</span>
                            </div>
                        )}

                        <button type="submit" className="btn-primary justify-center" disabled={loading}
                            style={{ marginTop: '4px', padding: '12px 20px' }}>
                            {loading ? (
                                <span className="flex items-center gap-2">
                                    <svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none">
                                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.3" />
                                        <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                                    </svg>
                                    Authenticating…
                                </span>
                            ) : <>Sign In to Platform &rarr;</>}
                        </button>
                    </form>
                </div>

                <div className="mt-6 flex items-center justify-center gap-6">
                    {[['1', 'Scope 1', 'var(--color-scope1)'], ['2', 'Scope 2', 'var(--color-scope2)'], ['3', 'Scope 3', 'var(--color-scope3)']].map(([num, label, color]) => (
                        <div key={num} className="flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full" style={{ background: color }} />
                            <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>{label}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}