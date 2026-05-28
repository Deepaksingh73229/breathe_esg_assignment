'use client';

import React, { useState, useEffect } from 'react';
import { FacilitiesService } from '@/services/facilities.service';
import { AuthService, UserProfile } from '@/services/auth.service';
import { Facility } from '@/lib/api';

export default function FacilitiesPage() {
    const [facilities, setFacilities] = useState<Facility[]>([]);
    const [user, setUser] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingFacility, setEditingFacility] = useState<Facility | null>(null);

    const [formData, setFormData] = useState({
        name: '',
        facility_type: 'office',
        sap_plant_code: '',
        utility_account_numbers: '', // Will split by comma
        organization: '',
    });

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [profile, facRes] = await Promise.all([
                    AuthService.getProfile(),
                    FacilitiesService.getFacilities()
                ]);
                setUser(profile);
                setFacilities(facRes.results);
                if (profile.organizations.length > 0) {
                    setFormData(prev => ({ ...prev, organization: profile.organizations[0].id }));
                }
            } catch (err) {
                console.error('Failed to load facilities', err);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const openModal = (facility?: Facility) => {
        if (facility) {
            setEditingFacility(facility);
            setFormData({
                name: facility.name,
                facility_type: facility.facility_type,
                sap_plant_code: facility.sap_plant_code || '',
                utility_account_numbers: (facility.utility_account_numbers || []).join(', '),
                organization: facility.organization,
            });
        } else {
            setEditingFacility(null);
            setFormData({
                name: '',
                facility_type: 'office',
                sap_plant_code: '',
                utility_account_numbers: '',
                organization: (user?.organizations && user.organizations.length > 0) ? user.organizations[0].id : '',
            });
        }
        setIsModalOpen(true);
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        const payload = {
            ...formData,
            utility_account_numbers: formData.utility_account_numbers
                .split(',')
                .map(s => s.trim())
                .filter(s => s !== '')
        };

        try {
            if (editingFacility) {
                await FacilitiesService.updateFacility(editingFacility.id, payload);
            } else {
                await FacilitiesService.createFacility(payload);
            }
            // Refresh list
            const updated = await FacilitiesService.getFacilities();
            setFacilities(updated.results);
            setIsModalOpen(false);
        } catch (err: any) {
            alert(err.message || 'Failed to save facility');
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm('Are you sure you want to delete this facility?')) return;
        try {
            await FacilitiesService.deleteFacility(id);
            setFacilities(facilities.filter(f => f.id !== id));
        } catch (err: any) {
            alert(err.message || 'Failed to delete facility');
        }
    };

    if (loading) return <div style={{ padding: '40px' }}>Loading facilities...</div>;

    return (
        <div style={{ padding: '32px 36px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '32px' }}>
                <div>
                    <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '1.8rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                        Facility <span style={{ color: 'var(--color-emerald)' }}>Management</span>
                    </h1>
                    <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
                        Register buildings, plants, and sites. Map them to SAP plant codes for automatic ingestion.
                    </p>
                </div>
                <button 
                    onClick={() => openModal()}
                    style={{ ...buttonStyle, background: 'var(--color-emerald)', color: '#080c14', width: 'auto' }}
                >
                    + Add Facility
                </button>
            </div>

            <div style={{ background: 'var(--color-navy-light)', borderRadius: '16px', border: '1px solid var(--color-border)', overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead style={{ background: 'rgba(255,255,255,0.03)', fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--color-text-muted)', letterSpacing: '0.05em' }}>
                        <tr>
                            <th style={thStyle}>Facility Name</th>
                            <th style={thStyle}>Type</th>
                            <th style={thStyle}>SAP Plant Code</th>
                            <th style={thStyle}>Utility Accounts</th>
                            <th style={thStyle}>Actions</th>
                        </tr>
                    </thead>
                    <tbody style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)' }}>
                        {facilities.length === 0 ? (
                            <tr>
                                <td colSpan={5} style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                                    No facilities registered yet. Add one to enable SAP data mapping.
                                </td>
                            </tr>
                        ) : facilities.map(f => (
                            <tr key={f.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                                <td style={tdStyle}>
                                    <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>{f.name}</div>
                                    <div style={{ fontSize: '0.75rem', opacity: 0.7 }}>{f.id}</div>
                                </td>
                                <td style={tdStyle}><span style={badgeStyle}>{f.facility_type}</span></td>
                                <td style={tdStyle}><code style={{ color: 'var(--color-emerald)' }}>{f.sap_plant_code || '—'}</code></td>
                                <td style={tdStyle}>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                                        {f.utility_account_numbers?.map(n => (
                                            <span key={n} style={{ fontSize: '0.75rem', background: 'var(--color-slate)', padding: '2px 6px', borderRadius: '4px' }}>{n}</span>
                                        )) || '—'}
                                    </div>
                                </td>
                                <td style={tdStyle}>
                                    <div style={{ display: 'flex', gap: '12px' }}>
                                        <button onClick={() => openModal(f)} style={actionButtonStyle}>Edit</button>
                                        <button onClick={() => handleDelete(f.id)} style={{ ...actionButtonStyle, color: '#ef4444' }}>Delete</button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Modal */}
            {isModalOpen && (
                <div style={modalOverlayStyle}>
                    <div style={modalContentStyle}>
                        <h2 style={{ marginBottom: '24px' }}>{editingFacility ? 'Edit Facility' : 'New Facility'}</h2>
                        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                            <div style={inputGroupStyle}>
                                <label style={labelStyle}>Facility Name</label>
                                <input 
                                    type="text" 
                                    required 
                                    value={formData.name}
                                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                                    style={inputStyle} 
                                    placeholder="e.g. Houston Manufacturing Plant"
                                />
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                                <div style={inputGroupStyle}>
                                    <label style={labelStyle}>Type</label>
                                    <select 
                                        value={formData.facility_type}
                                        onChange={e => setFormData({ ...formData, facility_type: e.target.value })}
                                        style={inputStyle}
                                    >
                                        <option value="office">Office</option>
                                        <option value="manufacturing">Manufacturing/Factory</option>
                                        <option value="warehouse">Warehouse/DC</option>
                                        <option value="data_center">Data Centre</option>
                                        <option value="retail">Retail Store</option>
                                        <option value="other">Other</option>
                                    </select>
                                </div>
                                <div style={inputGroupStyle}>
                                    <label style={labelStyle}>SAP Plant Code (Werk)</label>
                                    <input 
                                        type="text" 
                                        value={formData.sap_plant_code}
                                        onChange={e => setFormData({ ...formData, sap_plant_code: e.target.value })}
                                        style={inputStyle} 
                                        placeholder="e.g. US01"
                                    />
                                </div>
                            </div>
                            <div style={inputGroupStyle}>
                                <label style={labelStyle}>Utility Account Numbers (Comma separated)</label>
                                <input 
                                    type="text" 
                                    value={formData.utility_account_numbers}
                                    onChange={e => setFormData({ ...formData, utility_account_numbers: e.target.value })}
                                    style={inputStyle} 
                                    placeholder="ACCT-123, ACCT-456"
                                />
                            </div>
                            <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
                                <button type="submit" style={{ ...buttonStyle, background: 'var(--color-emerald)', color: '#080c14' }}>
                                    {editingFacility ? 'Update Facility' : 'Create Facility'}
                                </button>
                                <button type="button" onClick={() => setIsModalOpen(false)} style={{ ...buttonStyle, background: 'transparent', border: '1px solid var(--color-border)' }}>
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

const thStyle = { padding: '16px 20px', fontWeight: 600 };
const tdStyle = { padding: '16px 20px' };
const badgeStyle = { background: 'rgba(255,255,255,0.05)', padding: '4px 10px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 600 };
const actionButtonStyle = { background: 'none', border: 'none', color: 'var(--color-emerald)', cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600 };
const modalOverlayStyle: React.CSSProperties = { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 };
const modalContentStyle = { background: 'var(--color-navy)', padding: '32px', borderRadius: '20px', width: '500px', border: '1px solid var(--color-border)' };
const inputGroupStyle = { display: 'flex', flexDirection: 'column', gap: '8px' };
const labelStyle = { fontSize: '0.8rem', color: 'var(--color-text-secondary)' };
const inputStyle = { background: 'var(--color-navy-light)', border: '1px solid var(--color-border)', borderRadius: '8px', padding: '10px 14px', color: 'var(--color-text-primary)', outline: 'none' };
const buttonStyle = { width: '100%', padding: '12px', borderRadius: '10px', border: 'none', fontWeight: 700, cursor: 'pointer' };
