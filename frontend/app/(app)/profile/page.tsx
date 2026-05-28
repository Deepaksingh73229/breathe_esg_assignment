'use client';

import React, { useState, useEffect } from 'react';
import { AuthService, UserProfile } from '@/services/auth.service';

export default function ProfilePage() {
    const [user, setUser] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    const [formData, setFormData] = useState({
        first_name: '',
        last_name: '',
        email: ''
    });

    useEffect(() => {
        AuthService.getProfile()
            .then(profile => {
                setUser(profile);
                setFormData({
                    first_name: profile.first_name,
                    last_name: profile.last_name,
                    email: profile.email
                });
            })
            .finally(() => setLoading(false));
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        setError(null);
        setSuccess(false);

        try {
            const updated = await AuthService.updateProfile(formData);
            setUser(updated);
            setSuccess(true);
        } catch (err: any) {
            setError(err.message || 'Failed to update profile');
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <div style={{ padding: '40px' }}>Loading profile...</div>;

    return (
        <div style={{ padding: '40px', maxWidth: '800px' }}>
            <h1 style={{ color: 'var(--color-text-primary)', marginBottom: '8px' }}>Your Profile</h1>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '32px' }}>
                Manage your personal details and account settings.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '32px' }}>
                {/* Profile Form */}
                <div style={cardStyle}>
                    <h2 style={cardTitleStyle}>Personal Details</h2>
                    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                        <div style={inputGroupStyle}>
                            <label style={labelStyle}>First Name</label>
                            <input 
                                type="text"
                                value={formData.first_name}
                                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                                style={inputStyle}
                            />
                        </div>
                        <div style={inputGroupStyle}>
                            <label style={labelStyle}>Last Name</label>
                            <input 
                                type="text"
                                value={formData.last_name}
                                onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                                style={inputStyle}
                            />
                        </div>
                        <div style={inputGroupStyle}>
                            <label style={labelStyle}>Email Address</label>
                            <input 
                                type="email"
                                value={formData.email}
                                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                style={inputStyle}
                            />
                        </div>

                        {error && <div style={errorStyle}>{error}</div>}
                        {success && <div style={successStyle}>Profile updated successfully!</div>}

                        <button 
                            type="submit" 
                            disabled={saving}
                            style={{
                                ...buttonStyle,
                                cursor: saving ? 'not-allowed' : 'pointer',
                                opacity: saving ? 0.7 : 1,
                            }}
                        >
                            {saving ? 'Saving Changes...' : 'Save Profile'}
                        </button>
                    </form>
                </div>

                {/* Account Info */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                    <div style={cardStyle}>
                        <h2 style={cardTitleStyle}>Account Status</h2>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            <div style={infoItemStyle}>
                                <div style={infoLabelStyle}>User ID</div>
                                <div style={infoValueStyle}>{user?.id}</div>
                            </div>
                            <div style={infoItemStyle}>
                                <div style={infoLabelStyle}>Global Role</div>
                                <div style={infoValueStyle}>
                                    {user?.is_superuser ? (
                                        <span style={{ color: 'var(--color-emerald)' }}>System Superadmin</span>
                                    ) : (
                                        'Standard User'
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div style={cardStyle}>
                        <h2 style={cardTitleStyle}>Organizations</h2>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            {user?.organizations.map(org => (
                                <div key={org.id} style={orgItemStyle}>
                                    <div style={{ fontWeight: 600 }}>{org.name}</div>
                                    <div style={{ 
                                        fontSize: '0.7rem', 
                                        textTransform: 'uppercase', 
                                        letterSpacing: '0.05em',
                                        color: org.role === 'admin' ? 'var(--color-emerald)' : 'var(--color-text-muted)'
                                    }}>
                                        {org.role}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

const cardStyle = {
    background: 'var(--color-navy-light)',
    border: '1px solid var(--color-border)',
    borderRadius: '16px',
    padding: '24px'
};

const cardTitleStyle = {
    fontSize: '1rem',
    fontWeight: 600,
    marginBottom: '20px',
    color: 'var(--color-text-primary)'
};

const inputGroupStyle = {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px'
};

const labelStyle = {
    fontSize: '0.8rem',
    color: 'var(--color-text-secondary)'
};

const inputStyle = {
    width: '100%',
    background: 'var(--color-navy)',
    border: '1px solid var(--color-border)',
    borderRadius: '8px',
    padding: '12px',
    color: 'var(--color-text-primary)',
    fontSize: '0.95rem',
    outline: 'none',
};

const buttonStyle = {
    background: 'var(--color-emerald)',
    color: '#080c14',
    border: 'none',
    padding: '14px',
    borderRadius: '8px',
    fontWeight: 700,
    fontSize: '0.95rem',
    marginTop: '8px'
};

const infoItemStyle = {
    paddingBottom: '12px',
    borderBottom: '1px solid var(--color-border)'
};

const infoLabelStyle = {
    fontSize: '0.75rem',
    color: 'var(--color-text-muted)',
    marginBottom: '4px'
};

const infoValueStyle = {
    fontSize: '0.9rem',
    color: 'var(--color-text-primary)',
    wordBreak: 'break-all',
    fontFamily: 'var(--font-mono)'
};

const orgItemStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px',
    background: 'var(--color-navy)',
    borderRadius: '10px',
    border: '1px solid var(--color-border)'
};

const errorStyle = {
    padding: '10px',
    background: 'rgba(239,68,68,0.1)',
    color: '#ef4444',
    borderRadius: '6px',
    fontSize: '0.85rem'
};

const successStyle = {
    padding: '10px',
    background: 'rgba(0,232,122,0.1)',
    color: 'var(--color-emerald)',
    borderRadius: '6px',
    fontSize: '0.85rem'
};
