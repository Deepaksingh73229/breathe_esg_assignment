'use client';

import React, { useState, useRef, useEffect, CSSProperties } from 'react';
import { api, IngestionRun, IngestionResult } from '@/lib/api';
import { AuthService, UserProfile } from '@/services/auth.service';

const SOURCES = [
    { id: 'sap', label: 'SAP ERP — Fuel & Procurement', icon: '🏭', accept: '.csv', color: '#008eff' },
    { id: 'utility', label: 'Utility Portal — Electricity', icon: '⚡', accept: '.csv', color: '#ffb900' },
    { id: 'travel', label: 'Concur/Navan — Corporate Travel', icon: '✈️', accept: '.json', color: '#8e44ad' },
];

export default function IngestPage() {
    const [selectedSource, setSelectedSource] = useState(SOURCES[0]);
    const [file, setFile] = useState<File | null>(null);
    const [dragging, setDragging] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<IngestionResult | null>(null);
    const [user, setUser] = useState<UserProfile | null>(null);
    const [selectedOrgId, setSelectedOrgId] = useState('');
    const [history, setHistory] = useState<IngestionRun[]>([]);
    const [loadingHistory, setLoadingHistory] = useState(true);

    const fileRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        AuthService.getProfile().then(profile => {
            setUser(profile);
            if (profile.organizations.length > 0) {
                setSelectedOrgId(profile.organizations[0].id);
            }
        });
        fetchHistory();
    }, []);

    const fetchHistory = async () => {
        setLoadingHistory(true);
        try {
            const res = await api.getIngestionRuns();
            setHistory(res.results);
        } catch (err) {
            console.error('Failed to load history', err);
        } finally {
            setLoadingHistory(false);
        }
    };

    const onDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setDragging(false);
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile) setFile(droppedFile);
    };

    const handleUpload = async () => {
        if (!file || !selectedOrgId) return;
        setUploading(true);
        setError(null);
        setResult(null);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('source_type', selectedSource.id);
        formData.append('organization_id', selectedOrgId);

        try {
            const res = await api.uploadFile(formData);
            setResult(res);
            setFile(null);
            fetchHistory();
        } catch (err: any) {
            setError(err.message || 'Ingestion failed');
        } finally {
            setUploading(false);
        }
    };

    const pr = result?.pipeline_result;
    const successRate = pr ? Math.round((pr.valid_rows / pr.total_rows) * 100) : 0;

    return (
        <div style={{ padding: '40px', maxWidth: '800px' }}>
            <h1 style={{ color: 'var(--color-text-primary)', marginBottom: '8px' }}>Data Ingestion</h1>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '32px' }}>
                Upload raw exports from your source systems. Our pipeline will automatically normalize and calculate emissions.
            </p>

            {/* Source Selector */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '32px' }}>
                {SOURCES.map(source => (
                    <button
                        key={source.id}
                        onClick={() => { setSelectedSource(source); setFile(null); setError(null); }}
                        style={{
                            padding: '20px 12px',
                            borderRadius: '16px',
                            background: selectedSource.id === source.id ? 'var(--color-navy-light)' : 'transparent',
                            border: `2px solid ${selectedSource.id === source.id ? source.color : 'var(--color-border)'}`,
                            cursor: 'pointer',
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            gap: '12px',
                            transition: 'all 0.2s',
                        }}>
                        <span style={{ fontSize: '1.5rem' }}>{source.icon}</span>
                        <span style={{ 
                            fontSize: '0.75rem', 
                            fontWeight: 700, 
                            color: selectedSource.id === source.id ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
                            textAlign: 'center'
                        }}>
                            {source.label.split(' — ')[0]}
                        </span>
                    </button>
                ))}
            </div>

            {/* Org Selector (hidden if only one org) */}
            {user && user.organizations.length > 1 && (
                <div style={{ marginBottom: '24px' }}>
                    <label style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '8px' }}>Target Organization</label>
                    <select 
                        value={selectedOrgId}
                        onChange={(e) => setSelectedOrgId(e.target.value)}
                        style={{
                            width: '100%',
                            background: 'var(--color-navy-light)',
                            border: '1px solid var(--color-border)',
                            color: '#fff',
                            padding: '10px 14px',
                            borderRadius: '10px',
                            outline: 'none'
                        }}
                    >
                        {user.organizations.map(org => (
                            <option key={org.id} value={org.id}>{org.name}</option>
                        ))}
                    </select>
                </div>
            )}

            {/* Drop zone */}
            <div
                onDragOver={e => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                onClick={() => fileRef.current?.click()}
                style={{
                    marginBottom: '20px',
                    height: '180px',
                    borderRadius: '16px',
                    border: `2px dashed ${dragging ? selectedSource.color : file ? 'var(--color-emerald)' : 'var(--color-border)'}`,
                    background: dragging ? `${selectedSource.color}06` : file ? 'rgba(0,232,122,0.04)' : 'var(--color-navy)',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '10px',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                }}>
                <input ref={fileRef} type="file" accept={selectedSource.accept} style={{ display: 'none' }}
                    onChange={e => e.target.files?.[0] && setFile(e.target.files[0])} />
                {file ? (
                    <>
                        <div style={{ fontSize: '2rem' }}>📄</div>
                        <div style={{ fontWeight: 600, color: 'var(--color-emerald)', fontSize: '0.9rem' }}>{file.name}</div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                            {(file.size / 1024).toFixed(1)} KB · Click to replace
                        </div>
                    </>
                ) : (
                    <>
                        <div style={{ fontSize: '2rem', opacity: 0.5 }}>
                            {selectedSource.icon}
                        </div>
                        <div style={{ fontWeight: 600, color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
                            Drop {selectedSource.accept.toUpperCase()} file here
                        </div>
                        <div style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>or click to browse</div>
                    </>
                )}
            </div>

            {/* Upload button */}
            {error && (
                <div style={{ marginBottom: '16px', padding: '12px 16px', borderRadius: '10px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)' }}>
                    <span style={{ color: '#ef4444', fontSize: '0.875rem' }}>⚠ {error}</span>
                </div>
            )}

            <button
                className="btn-primary"
                onClick={handleUpload}
                disabled={!file || !selectedOrgId || uploading}
                style={{ opacity: (!file || !selectedOrgId) ? 0.5 : 1, padding: '12px 28px', fontSize: '0.9rem', width: '100%', justifyContent: 'center', marginBottom: '40px' }}>
                {uploading ? (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <svg className="animate-spin" width="18" height="18" viewBox="0 0 24 24" fill="none">
                            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.3" />
                            <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                        </svg>
                        Processing pipeline…
                    </span>
                ) : `Upload & Process ${selectedSource.label.split(' — ')[0]} File →`}
            </button>

            {/* Ingestion History */}
            <div style={{ marginTop: '40px' }}>
                <h2 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '20px', color: 'var(--color-text-primary)' }}>Ingestion History</h2>
                <div style={{ background: 'var(--color-navy-light)', borderRadius: '16px', border: '1px solid var(--color-border)', overflow: 'hidden' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                        <thead style={{ background: 'rgba(255,255,255,0.03)', fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--color-text-muted)', letterSpacing: '0.05em' }}>
                            <tr>
                                <th style={{ padding: '12px 20px' }}>Date</th>
                                <th style={{ padding: '12px 20px' }}>Source</th>
                                <th style={{ padding: '12px 20px' }}>Status</th>
                                <th style={{ padding: '12px 20px', textAlign: 'right' }}>Rows</th>
                                <th style={{ padding: '12px 20px', textAlign: 'right' }}>Success</th>
                            </tr>
                        </thead>
                        <tbody style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                            {loadingHistory ? (
                                <tr><td colSpan={5} style={{ padding: '20px', textAlign: 'center' }}>Loading history...</td></tr>
                            ) : history.length === 0 ? (
                                <tr><td colSpan={5} style={{ padding: '20px', textAlign: 'center' }}>No ingestion history found.</td></tr>
                            ) : history.map(run => (
                                <tr key={run.id} style={{ borderTop: '1px solid var(--color-border)' }}>
                                    <td style={{ padding: '12px 20px' }}>{new Date(run.created_at).toLocaleDateString()}</td>
                                    <td style={{ padding: '12px 20px' }}><span style={{ textTransform: 'uppercase', fontSize: '0.7rem', fontFamily: 'var(--font-mono)' }}>{run.source_type}</span></td>
                                    <td style={{ padding: '12px 20px' }}>
                                        <span style={{ 
                                            padding: '4px 10px', borderRadius: '6px', fontSize: '0.7rem', fontWeight: 700,
                                            background: run.status === 'parsed' ? 'rgba(0,232,122,0.1)' : run.status === 'failed' ? 'rgba(239,68,68,0.1)' : 'rgba(251,191,36,0.1)',
                                            color: run.status === 'parsed' ? 'var(--color-emerald)' : run.status === 'failed' ? '#ef4444' : 'var(--color-pending)'
                                        }}>
                                            {run.status.toUpperCase()}
                                        </span>
                                    </td>
                                    <td style={{ padding: '12px 20px', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{run.total_rows}</td>
                                    <td style={{ padding: '12px 20px', textAlign: 'right', fontFamily: 'var(--font-mono)', color: 'var(--color-emerald)' }}>{run.valid_rows}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Result Overlay */}
            {result && pr && (
                <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
                    <div style={{ background: 'var(--color-navy)', padding: '32px', borderRadius: '24px', width: '600px', border: '1px solid var(--color-border)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                            <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Pipeline Result</h3>
                            <button onClick={() => setResult(null)} style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: '1.5rem' }}>×</button>
                        </div>
                        
                        <div style={{ marginBottom: '24px', padding: '20px', borderRadius: '16px', background: 'var(--color-slate)', border: `1px solid ${pr.status === 'parsed' ? 'rgba(0,232,122,0.3)' : 'rgba(251,191,36,0.3)'}` }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>Success Rate</span>
                                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-emerald)' }}>{successRate}%</span>
                            </div>
                            <div style={{ height: '8px', borderRadius: '100px', background: 'var(--color-navy)', overflow: 'hidden' }}>
                                <div style={{ height: '100%', background: 'var(--color-emerald)', width: `${successRate}%` }} />
                            </div>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
                            <div style={statBoxStyle}>
                                <div style={statLabelStyle}>Total Rows</div>
                                <div style={statValueStyle}>{pr.total_rows}</div>
                            </div>
                            <div style={statBoxStyle}>
                                <div style={statLabelStyle}>Valid Records</div>
                                <div style={{ ...statValueStyle, color: 'var(--color-emerald)' }}>{pr.valid_rows}</div>
                            </div>
                        </div>

                        <button onClick={() => setResult(null)} style={{ ...btnStyle, background: 'var(--color-emerald)', color: '#080c14' }}>
                            Close & View History
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

const statBoxStyle: CSSProperties = { background: 'var(--color-navy-light)', padding: '16px', borderRadius: '12px', border: '1px solid var(--color-border)' };
const statLabelStyle: CSSProperties = { fontSize: '0.7rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' };
const statValueStyle: CSSProperties = { fontSize: '1.4rem', fontWeight: 700, fontFamily: 'var(--font-mono)' };
const btnStyle: CSSProperties = { width: '100%', padding: '14px', borderRadius: '12px', border: 'none', fontWeight: 700, cursor: 'pointer' };
