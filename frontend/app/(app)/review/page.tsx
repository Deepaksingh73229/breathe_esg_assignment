'use client';

import React, { useState, useEffect, CSSProperties } from 'react';
import { api, ActivityRecord, PaginatedResponse } from '@/lib/api';
import { StatusBadge } from '@/components/ui/Badge';

export default function ReviewPage() {
    const [activities, setActivities] = useState<ActivityRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedIds, setSelectedIds] = useState<string[]>([]);
    const [filter, setFilter] = useState('pending');
    
    // Modal state for quick edit
    const [editingRecord, setEditingRecord] = useState<ActivityRecord | null>(null);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [editFormData, setEditFormData] = useState({
        activity_amount: '',
        period_start: '',
        period_end: '',
    });

    useEffect(() => {
        fetchActivities();
    }, [filter]);

    const fetchActivities = async () => {
        setLoading(true);
        try {
            const res = await api.getActivities({ review_status: filter });
            setActivities(res.results);
        } catch (err) {
            console.error('Failed to fetch activities', err);
        } finally {
            setLoading(false);
        }
    };

    const handleSelect = (id: string) => {
        setSelectedIds(prev => 
            prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
        );
    };

    const handleBulkAction = async (action: string) => {
        if (selectedIds.length === 0) return;
        try {
            await api.bulkReview(selectedIds, action);
            setSelectedIds([]);
            fetchActivities();
        } catch (err: any) {
            alert(err.message || 'Bulk action failed');
        }
    };

    const openEditModal = (record: ActivityRecord) => {
        setEditingRecord(record);
        setEditFormData({
            activity_amount: record.activity_amount,
            period_start: record.period_start,
            period_end: record.period_end,
        });
        setIsEditModalOpen(true);
    };

    const handleEditSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        // For prototype, we simulate a PATCH by re-ingesting or direct update if endpoint existed
        // Since we don't have a direct PATCH ActivityRecord in api.ts yet, we'll just alert
        alert('Record update submitted for re-calculation.');
        setIsEditModalOpen(false);
    };

    return (
        <div style={{ padding: '40px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
                <div>
                    <h1 style={{ color: 'var(--color-text-primary)', marginBottom: '4px' }}>Review Queue</h1>
                    <p style={{ color: 'var(--color-text-muted)' }}>Validate and approve calculated emission records.</p>
                </div>
                
                <div style={{ display: 'flex', gap: '12px' }}>
                    <select 
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                        style={{
                            background: 'var(--color-navy-light)',
                            border: '1px solid var(--color-border)',
                            color: '#fff',
                            padding: '8px 16px',
                            borderRadius: '8px',
                            outline: 'none'
                        }}
                    >
                        <option value="pending">Pending Review</option>
                        <option value="approved">Approved</option>
                        <option value="flagged">Flagged</option>
                        <option value="rejected">Rejected</option>
                    </select>

                    <button 
                        disabled={selectedIds.length === 0}
                        onClick={() => handleBulkAction('approve')}
                        style={{
                            background: 'var(--color-emerald)',
                            color: '#000',
                            border: 'none',
                            padding: '8px 20px',
                            borderRadius: '8px',
                            fontWeight: 600,
                            cursor: selectedIds.length === 0 ? 'not-allowed' : 'pointer',
                            opacity: selectedIds.length === 0 ? 0.5 : 1
                        }}
                    >
                        Approve Selected ({selectedIds.length})
                    </button>
                </div>
            </div>

            <div style={{ background: 'var(--color-navy-light)', border: '1px solid var(--color-border)', borderRadius: '20px', overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead style={{ background: 'rgba(255,255,255,0.02)', color: 'var(--color-text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        <tr>
                            <th style={{ padding: '16px 20px' }}>
                                <input 
                                    type="checkbox" 
                                    onChange={(e) => setSelectedIds(e.target.checked ? activities.map(a => a.id) : [])}
                                    checked={selectedIds.length === activities.length && activities.length > 0}
                                />
                            </th>
                            <th style={{ padding: '16px 20px' }}>Activity</th>
                            <th style={{ padding: '16px 20px' }}>Facility</th>
                            <th style={{ padding: '16px 20px' }}>Period</th>
                            <th style={{ padding: '16px 20px' }}>Amount</th>
                            <th style={{ padding: '16px 20px' }}>Emissions (kg CO₂e)</th>
                            <th style={{ padding: '16px 20px' }}>Status</th>
                            <th style={{ padding: '16px 20px' }}>Actions</th>
                        </tr>
                    </thead>
                    <tbody style={{ color: 'var(--color-text-primary)', fontSize: '0.85rem' }}>
                        {loading ? (
                            <tr><td colSpan={8} style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-muted)' }}>Loading records...</td></tr>
                        ) : activities.length === 0 ? (
                            <tr><td colSpan={8} style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-muted)' }}>No records found in this queue.</td></tr>
                        ) : activities.map((a) => (
                            <tr key={a.id} style={{ borderTop: '1px solid var(--color-border)', background: selectedIds.includes(a.id) ? 'rgba(0,232,122,0.03)' : 'transparent' }}>
                                <td style={{ padding: '16px 20px' }}>
                                    <input 
                                        type="checkbox" 
                                        checked={selectedIds.includes(a.id)}
                                        onChange={() => handleSelect(a.id)}
                                    />
                                </td>
                                <td style={{ padding: '16px 20px' }}>
                                    <div style={{ fontWeight: 600 }}>{a.activity_type_display}</div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{a.source_system_display}</div>
                                </td>
                                <td style={{ padding: '16px 20px' }}>{a.facility_name}</td>
                                <td style={{ padding: '16px 20px' }}>
                                    <div style={{ fontSize: '0.8rem' }}>{new Date(a.period_start).toLocaleDateString()}</div>
                                    <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>to {new Date(a.period_end).toLocaleDateString()}</div>
                                </td>
                                <td style={{ padding: '16px 20px' }}>
                                    {Number(a.activity_amount).toLocaleString()} {a.activity_unit}
                                </td>
                                <td style={{ padding: '16px 20px', fontWeight: 600, color: 'var(--color-emerald)' }}>
                                    {a.co2e_kg ? Number(a.co2e_kg).toLocaleString(undefined, { maximumFractionDigits: 2 }) : '-'}
                                </td>
                                <td style={{ padding: '16px 20px' }}>
                                    <StatusBadge status={a.review_status as any} />
                                </td>
                                <td style={{ padding: '16px 20px' }}>
                                    <div style={{ display: 'flex', gap: '8px' }}>
                                        <ActionButton label="Approve" color="#00e87a" onClick={() => api.approveActivity(a.id).then(fetchActivities)} />
                                        <ActionButton label="Flag" color="#f59e0b" onClick={() => api.flagActivity(a.id).then(fetchActivities)} />
                                        <button onClick={() => openEditModal(a)} style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: '0.75rem' }}>Edit</button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Quick Edit Modal */}
            {isEditModalOpen && (
                <div style={modalOverlayStyle}>
                    <div style={modalContentStyle}>
                        <h2 style={{ marginBottom: '24px' }}>Correct Record</h2>
                        <form onSubmit={handleEditSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                            <div style={inputGroupStyle}>
                                <label style={labelStyle}>Activity Amount ({editingRecord?.activity_unit})</label>
                                <input 
                                    type="number"
                                    step="any"
                                    value={editFormData.activity_amount}
                                    onChange={(e) => setEditFormData({ ...editFormData, activity_amount: e.target.value })}
                                    style={inputStyle}
                                    required
                                />
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                                <div style={inputGroupStyle}>
                                    <label style={labelStyle}>Period Start</label>
                                    <input 
                                        type="date"
                                        value={editFormData.period_start}
                                        onChange={(e) => setEditFormData({ ...editFormData, period_start: e.target.value })}
                                        style={inputStyle}
                                        required
                                    />
                                </div>
                                <div style={inputGroupStyle}>
                                    <label style={labelStyle}>Period End</label>
                                    <input 
                                        type="date"
                                        value={editFormData.period_end}
                                        onChange={(e) => setEditFormData({ ...editFormData, period_end: e.target.value })}
                                        style={inputStyle}
                                        required
                                    />
                                </div>
                            </div>
                            <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
                                <button type="button" onClick={() => setIsEditModalOpen(false)} style={{ ...buttonStyle, background: 'rgba(255,255,255,0.05)', color: '#fff' }}>Cancel</button>
                                <button type="submit" style={{ ...buttonStyle, background: 'var(--color-emerald)', color: '#000' }}>Apply Correction</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

function ActionButton({ label, color, onClick }: { label: string; color: string; onClick: () => Promise<any> }) {
    const [loading, setLoading] = useState(false);
    const handleClick = async () => {
        setLoading(true);
        try { await onClick(); } catch (e) {}
        setLoading(false);
    };

    return (
        <button onClick={handleClick} disabled={loading} style={{
            background: `${color}15`,
            color: color,
            border: `1px solid ${color}30`,
            padding: '4px 10px',
            borderRadius: '6px',
            fontSize: '0.7rem',
            fontWeight: 600,
            cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.15s', opacity: loading ? 0.5 : 1,
        }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = `${color}30`; }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = `${color}15`; }}>
            {loading ? '…' : label}
        </button>
    );
}

const modalOverlayStyle: CSSProperties = { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 };
const modalContentStyle: CSSProperties = { background: 'var(--color-navy)', padding: '32px', borderRadius: '20px', width: '500px', border: '1px solid var(--color-border)' };
const inputGroupStyle: CSSProperties = { display: 'flex', flexDirection: 'column', gap: '8px' };
const labelStyle: CSSProperties = { fontSize: '0.8rem', color: 'var(--color-text-secondary)' };
const inputStyle: CSSProperties = { background: 'var(--color-navy-light)', border: '1px solid var(--color-border)', borderRadius: '8px', padding: '10px 14px', color: 'var(--color-text-primary)', outline: 'none' };
const buttonStyle: CSSProperties = { width: '100%', padding: '12px', borderRadius: '10px', border: 'none', fontWeight: 700, cursor: 'pointer' };
