'use client';
import { useEffect, useState, useCallback } from 'react';
import { api, ActivityRecord } from '@/lib/api';
import { formatCO2e, formatDate } from '@/lib/utils';
import { StatusBadge, ScopeBadge, SourceBadge } from '@/components/ui/Badge';

const SCOPES = ['', '1', '2', '3'];
const STATUSES = ['pending', 'flagged', 'approved', 'rejected'];
const SOURCES = ['', 'sap', 'utility', 'travel'];

export default function ReviewPage() {
    const [records, setRecords] = useState<ActivityRecord[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [selected, setSelected] = useState<Set<string>>(new Set());
    const [scopeFilter, setScopeFilter] = useState('');
    const [statusFilter, setStatusFilter] = useState('pending');
    const [sourceFilter, setSourceFilter] = useState('');
    const [page, setPage] = useState(1);
    const [actionLoading, setActionLoading] = useState('');
    const [notes, setNotes] = useState('');
    const [showNotesFor, setShowNotesFor] = useState<string | null>(null);
    const [editingRecord, setEditingRecord] = useState<ActivityRecord | null>(null);
    const [editForm, setEditForm] = useState({
        activity_amount: '',
        period_start: '',
        period_end: '',
    });

    const loadRecords = useCallback(async () => {
        setLoading(true);
        try {
            const params: Record<string, string> = { page: String(page), page_size: '20' };
            if (scopeFilter) params.scope = scopeFilter;
            if (statusFilter) params.review_status = statusFilter;
            if (sourceFilter) params.source_system = sourceFilter;
            const data = await api.getActivities(params);
            setRecords(data.results);
            setTotal(data.count);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    }, [page, scopeFilter, statusFilter, sourceFilter]);

    useEffect(() => { loadRecords(); }, [loadRecords]);

    async function handleSingleAction(id: string, action: 'approve' | 'reject' | 'flag') {
        setActionLoading(id + action);
        try {
            if (action === 'approve') await api.approveActivity(id, notes);
            else if (action === 'reject') await api.rejectActivity(id, notes);
            else await api.flagActivity(id, notes);
            setShowNotesFor(null);
            setNotes('');
            loadRecords();
        } catch (e) { console.error(e); }
        finally { setActionLoading(''); }
    }

    async function handleBulkAction(action: string) {
        if (!selected.size) return;
        setActionLoading('bulk');
        try {
            await api.bulkReview([...selected], action, notes);
            setSelected(new Set());
            setNotes('');
            loadRecords();
        } catch (e) { console.error(e); }
        finally { setActionLoading(''); }
    }

    function toggleSelect(id: string) {
        const s = new Set(selected);
        s.has(id) ? s.delete(id) : s.add(id);
        setSelected(s);
    }

    function toggleAll() {
        if (selected.size === records.length) setSelected(new Set());
        else setSelected(new Set(records.map(r => r.id)));
    }

    const openEditModal = (r: ActivityRecord) => {
        setEditingRecord(r);
        setEditForm({
            activity_amount: String(r.activity_amount),
            period_start: r.period_start,
            period_end: r.period_end,
        });
    };

    const handleEditSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingRecord) return;
        setActionLoading('editing');
        try {
            await api.editActivity(editingRecord.id, editForm);
            setEditingRecord(null);
            loadRecords();
        } catch (err: any) {
            alert(err.message || 'Failed to update record');
        } finally {
            setActionLoading('');
        }
    };

    const totalPages = Math.ceil(total / 20);

    return (
        <div style={{ padding: '32px 36px' }}>
            {/* Header */}
            <div style={{ marginBottom: '28px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--color-text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '6px' }}>Analyst Workflow</p>
                    <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 700, color: 'var(--color-text-primary)', letterSpacing: '-0.03em' }}>
                        Review <span style={{ color: 'var(--color-emerald)' }}>Queue</span>
                    </h1>
                    <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem', marginTop: '4px' }}>
                        {total} records · Approve, reject, or flag for attention
                    </p>
                </div>

                {/* Bulk actions */}
                {selected.size > 0 && (
                    <div className="animate-fade-in" style={{ display: 'flex', gap: '8px', alignItems: 'center', padding: '10px 16px', borderRadius: '12px', background: 'var(--color-navy-light)', border: '1px solid var(--color-border)' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginRight: '4px' }}>
                            {selected.size} selected
                        </span>
                        {['approve', 'flag', 'reject'].map(a => (
                            <button key={a} onClick={() => handleBulkAction(a)} disabled={actionLoading === 'bulk'}
                                style={{
                                    padding: '6px 14px', borderRadius: '8px', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer', border: 'none',
                                    background: a === 'approve' ? 'var(--color-emerald)' : a === 'flag' ? 'var(--color-flagged)' : 'var(--color-rejected)',
                                    color: a === 'approve' ? 'var(--color-obsidian)' : '#fff',
                                    opacity: actionLoading === 'bulk' ? 0.6 : 1,
                                }}>
                                {a.charAt(0).toUpperCase() + a.slice(1)} All
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {/* Filters */}
            <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
                {/* Status tabs */}
                <div style={{ display: 'flex', background: 'var(--color-navy)', borderRadius: '10px', border: '1px solid var(--color-border)', padding: '4px', gap: '2px' }}>
                    {STATUSES.map(s => (
                        <button key={s} onClick={() => { setStatusFilter(s); setPage(1); }}
                            style={{
                                padding: '6px 14px', borderRadius: '7px', fontSize: '0.8rem', fontWeight: 500, cursor: 'pointer',
                                background: statusFilter === s ? 'var(--color-slate)' : 'transparent',
                                border: 'none',
                                color: statusFilter === s ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
                                transition: 'all 0.15s',
                            }}>
                            {s === 'pending' ? '⏳ Pending' : s === 'flagged' ? '🚩 Flagged' : s === 'approved' ? '✓ Approved' : '✕ Rejected'}
                        </button>
                    ))}
                </div>

                <select value={scopeFilter} onChange={e => { setScopeFilter(e.target.value); setPage(1); }}
                    className="input-base" style={{ width: 'auto', paddingRight: '32px' }}>
                    <option value="">All Scopes</option>
                    {SCOPES.filter(Boolean).map(s => <option key={s} value={s}>Scope {s}</option>)}
                </select>

                <select value={sourceFilter} onChange={e => { setSourceFilter(e.target.value); setPage(1); }}
                    className="input-base" style={{ width: 'auto', paddingRight: '32px' }}>
                    <option value="">All Sources</option>
                    {SOURCES.filter(Boolean).map(s => <option key={s} value={s}>{s.toUpperCase()}</option>)}
                </select>
            </div>

            {/* Table */}
            <div className="card" style={{ overflow: 'hidden', marginBottom: '16px' }}>
                {loading ? (
                    <div style={{ padding: '60px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                        <div style={{ fontSize: '0.9rem' }}>Loading records…</div>
                    </div>
                ) : records.length === 0 ? (
                    <div style={{ padding: '60px', textAlign: 'center' }}>
                        <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>🎯</div>
                        <p style={{ color: 'var(--color-text-primary)', fontWeight: 600, marginBottom: '4px' }}>No records found</p>
                        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>Try adjusting the filters above</p>
                    </div>
                ) : (
                    <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr>
                                <th style={{ width: '40px', textAlign: 'center' }}>
                                    <input type="checkbox" checked={selected.size === records.length && records.length > 0}
                                        onChange={toggleAll} style={{ cursor: 'pointer', accentColor: 'var(--color-emerald)' }} />
                                </th>
                                <th>Source</th>
                                <th>Facility</th>
                                <th>Activity Type</th>
                                <th>Period</th>
                                <th style={{ textAlign: 'right' }}>Amount</th>
                                <th style={{ textAlign: 'right' }}>CO₂e</th>
                                <th>Status</th>
                                <th style={{ textAlign: 'center' }}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {records.map(r => (
                                <tr key={r.id} style={{ background: selected.has(r.id) ? 'rgba(0,232,122,0.04)' : undefined }}>
                                    <td style={{ textAlign: 'center' }}>
                                        <input type="checkbox" checked={selected.has(r.id)} onChange={() => toggleSelect(r.id)}
                                            style={{ cursor: 'pointer', accentColor: 'var(--color-emerald)' }} />
                                    </td>
                                    <td>
                                        <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
                                            <SourceBadge source={r.source_system} />
                                            <ScopeBadge scope={r.scope} />
                                        </div>
                                    </td>
                                    <td style={{ color: 'var(--color-text-secondary)', maxWidth: '130px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.82rem' }}>
                                        {r.facility_name || 'Unassigned'}
                                        {r.is_estimated && <span style={{ marginLeft: '6px', fontSize: '0.65rem', color: 'var(--color-pending)', fontFamily: 'var(--font-mono)' }}>EST</span>}
                                    </td>
                                    <td style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {r.activity_type_display}
                                    </td>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
                                        {formatDate(r.period_start)}
                                        {r.period_end !== r.period_start && <><br />{formatDate(r.period_end)}</>}
                                    </td>
                                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--color-text-secondary)', whiteSpace: 'nowrap' }}>
                                        {parseFloat(r.activity_amount).toLocaleString('en-US', { maximumFractionDigits: 1 })} {r.activity_unit}
                                    </td>
                                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: r.co2e_kg ? 'var(--color-text-primary)' : 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
                                        {r.co2e_kg ? formatCO2e(parseFloat(r.co2e_kg)) : '—'}
                                    </td>
                                    <td><StatusBadge status={r.review_status} size="sm" /></td>
                                    <td style={{ textAlign: 'center' }}>
                                        <div style={{ display: 'flex', gap: '4px', justifyContent: 'center' }}>
                                            <ActionBtn label="✎" color="#a78bfa" title="Edit"
                                                loading={false}
                                                onClick={() => openEditModal(r)} />
                                            <ActionBtn label="✓" color="var(--color-emerald)" title="Approve"
                                                loading={actionLoading === r.id + 'approve'}
                                                onClick={() => handleSingleAction(r.id, 'approve')} />
                                            <ActionBtn label="⚑" color="var(--color-flagged)" title="Flag"
                                                loading={actionLoading === r.id + 'flag'}
                                                onClick={() => handleSingleAction(r.id, 'flag')} />
                                            <ActionBtn label="✕" color="#ef4444" title="Reject"
                                                loading={actionLoading === r.id + 'reject'}
                                                onClick={() => handleSingleAction(r.id, 'reject')} />
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', alignItems: 'center', marginBottom: '24px' }}>
                    <button className="btn-ghost" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} style={{ padding: '6px 14px', fontSize: '0.8rem' }}>← Prev</button>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
                        Page {page} of {totalPages}
                    </span>
                    <button className="btn-ghost" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} style={{ padding: '6px 14px', fontSize: '0.8rem' }}>Next →</button>
                </div>
            )}

            {/* Edit Modal */}
            {editingRecord && (
                <div style={modalOverlayStyle}>
                    <div style={modalContentStyle}>
                        <h2 style={{ marginBottom: '8px', color: 'var(--color-text-primary)' }}>Edit Record</h2>
                        <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginBottom: '24px' }}>
                            Adjust activity values or period dates. Emissions will be re-calculated automatically.
                        </p>
                        <form onSubmit={handleEditSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                            <div style={inputGroupStyle}>
                                <label style={labelStyle}>Activity Amount ({editingRecord.activity_unit})</label>
                                <input 
                                    type="number" step="any" required 
                                    value={editForm.activity_amount}
                                    onChange={e => setEditForm({ ...editForm, activity_amount: e.target.value })}
                                    style={inputStyle} 
                                />
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                                <div style={inputGroupStyle}>
                                    <label style={labelStyle}>Period Start</label>
                                    <input 
                                        type="date" required 
                                        value={editForm.period_start}
                                        onChange={e => setEditForm({ ...editForm, period_start: e.target.value })}
                                        style={inputStyle} 
                                    />
                                </div>
                                <div style={inputGroupStyle}>
                                    <label style={labelStyle}>Period End</label>
                                    <input 
                                        type="date" required 
                                        value={editForm.period_end}
                                        onChange={e => setEditForm({ ...editForm, period_end: e.target.value })}
                                        style={inputStyle} 
                                    />
                                </div>
                            </div>
                            <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
                                <button type="submit" disabled={actionLoading === 'editing'} 
                                    style={{ ...buttonStyle, background: 'var(--color-emerald)', color: '#080c14' }}>
                                    {actionLoading === 'editing' ? 'Saving...' : 'Save & Re-calculate'}
                                </button>
                                <button type="button" onClick={() => setEditingRecord(null)} 
                                    style={{ ...buttonStyle, background: 'transparent', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }}>
                                    Cancel
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

function ActionBtn({ label, color, title, loading, onClick }: { label: string; color: string; title: string; loading: boolean; onClick: () => void }) {
    return (
        <button title={title} onClick={onClick} disabled={loading} style={{
            width: '28px', height: '28px', borderRadius: '7px', border: 'none',
            background: `${color}15`, color, fontSize: '0.85rem', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.15s', opacity: loading ? 0.5 : 1,
        }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = `${color}30`; }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = `${color}15`; }}>
            {loading ? '…' : label}
        </button>
    );
}

const modalOverlayStyle: React.CSSProperties = { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 };
const modalContentStyle = { background: 'var(--color-navy)', padding: '32px', borderRadius: '20px', width: '500px', border: '1px solid var(--color-border)' };
const inputGroupStyle = { display: 'flex', flexDirection: 'column', gap: '8px' };
const labelStyle = { fontSize: '0.8rem', color: 'var(--color-text-secondary)' };
const inputStyle = { background: 'var(--color-navy-light)', border: '1px solid var(--color-border)', borderRadius: '8px', padding: '10px 14px', color: 'var(--color-text-primary)', outline: 'none' };
const buttonStyle = { width: '100%', padding: '12px', borderRadius: '10px', border: 'none', fontWeight: 700, cursor: 'pointer' };
