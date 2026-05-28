'use client';

import React, { useState, useEffect, CSSProperties } from 'react';
import { AuthService, UserProfile } from '@/services/auth.service';

export default function ProfilePage() {
    const [user, setUser] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);
    const [formData, setFormData] = useState({
        first_name: '',
        last_name: '',
        email: ''
    });

    useEffect(() => {
        AuthService.getProfile().then(profile => {
            setUser(profile);
            setFormData({
                first_name: profile.first_name,
                last_name: profile.last_name,
                email: profile.email
            });
        });
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setSuccess(false);
        try {
            await AuthService.updateProfile(formData);
            setSuccess(true);
            const updated = await AuthService.getProfile();
            setUser(updated);
        } catch (err: any) {
            setError(err.message || 'Failed to update profile');
        } finally {
            setLoading(false);
        }
    };

    if (!user) return <div style={{ padding: '40px' }}>Loading profile...</div>;

    return (
        <div style={{ padding: '40px', maxWidth: '1000px' }}>
            <h1 style={{ color: 'var(--color-text-primary)', marginBottom: '32px' }}>User Profile</h1>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: '40px' }}>
                
                {/* Left Column: Edit Form */}
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
                            <label style={labelStyle}>Email Address (Login)</label>
                            <input 
                                type="email"
                                value={formData.email}
                                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                style={inputStyle}
                                disabled
                            />
                            <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '4px' }}>
                                Email cannot be changed by the user. Contact an administrator.
                            </p>
                        </div>

                        {error && <div style={errorStyle}>{error}</div>}
                        {success && <div style={successStyle}>Profile updated successfully!</div>}

                        <button 
                            type="submit" 
                            disabled={loading}
                            style={{ ...buttonStyle, opacity: loading ? 0.7 : 1, cursor: loading ? 'not-allowed' : 'pointer' }}
                        >
                            {loading ? 'Saving Changes...' : 'Update Profile'}
                        </button>
                    </form>
                </div>

                {/* Right Column: Account Info */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                    
                    <div style={cardStyle}>
                        <h2 style={cardTitleStyle}>Security Tokens</h2>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            <div style={infoItemStyle}>
                                <div style={infoLabelStyle}>Active API Token</div>
                                <div style={infoValueStyle}>
                                    {typeof window !== 'undefined' ? localStorage.getItem('breathe_token')?.substring(0, 8) + '...' : '******'}
                                </div>
                            </div>
                            <button 
                                onClick={() => {
                                    const token = localStorage.getItem('breathe_token');
                                    if (token) navigator.clipboard.writeText(token).then(() => alert('Token copied to clipboard'));
                                }}
                                style={{ ...buttonStyle, background: 'rgba(255,255,255,0.05)', color: '#fff', marginTop: '0' }}
                            >
                                Copy API Token
                            </button>
                        </div>
                    </div>

                    <div style={cardStyle}>
                        <h2 style={cardTitleStyle}>Organizations</h2>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            {user.organizations.map(membership => (
                                <div key={membership.id} style={orgItemStyle}>
                                    <div>
                                        <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{membership.name}</div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', textTransform: 'capitalize' }}>{membership.role}</div>
                                    </div>
                                    <div style={{ color: 'var(--color-emerald)', fontSize: '0.75rem', fontWeight: 600 }}>Active</div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

const cardStyle: CSSProperties = {
    background: 'var(--color-navy-light)',
    border: '1px solid var(--color-border)',
    borderRadius: '20px',
    padding: '32px'
};

const cardTitleStyle: CSSProperties = {
    fontSize: '1rem',
    fontWeight: 600,
    marginBottom: '20px',
    color: 'var(--color-text-primary)'
};

const inputGroupStyle: CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px'
};

const labelStyle: CSSProperties = {
    fontSize: '0.8rem',
    color: 'var(--color-text-secondary)'
};

const inputStyle: CSSProperties = {
    width: '100%',
    background: 'var(--color-navy)',
    border: '1px solid var(--color-border)',
    borderRadius: '8px',
    padding: '12px',
    color: 'var(--color-text-primary)',
    fontSize: '0.95rem',
    outline: 'none',
};

const buttonStyle: CSSProperties = {
    background: 'var(--color-emerald)',
    color: '#080c14',
    border: 'none',
    padding: '14px',
    borderRadius: '8px',
    fontWeight: 700,
    fontSize: '0.95rem',
    marginTop: '8px'
};

const infoItemStyle: CSSProperties = {
    paddingBottom: '12px',
    borderBottom: '1px solid var(--color-border)'
};

const infoLabelStyle: CSSProperties = {
    fontSize: '0.75rem',
    color: 'var(--color-text-muted)',
    marginBottom: '4px'
};

const infoValueStyle: CSSProperties = {
    fontSize: '0.9rem',
    color: 'var(--color-text-primary)',
    wordBreak: 'break-all',
    fontFamily: 'var(--font-mono)'
};

const orgItemStyle: CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px',
    background: 'var(--color-navy)',
    borderRadius: '10px',
    border: '1px solid var(--color-border)'
};

const errorStyle: CSSProperties = {
    padding: '10px',
    background: 'rgba(239,68,68,0.1)',
    color: '#ef4444',
    borderRadius: '6px',
    fontSize: '0.85rem'
};

const successStyle: CSSProperties = {
    padding: '10px',
    background: 'rgba(0,232,122,0.1)',
    color: 'var(--color-emerald)',
    borderRadius: '6px',
    fontSize: '0.85rem'
};
