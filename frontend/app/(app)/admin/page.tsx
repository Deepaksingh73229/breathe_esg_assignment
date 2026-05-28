'use client';

import React, { useState, useEffect } from 'react';
import { OrganizationService } from '@/services/organization.service';
import { AuthService, UserProfile } from '@/services/auth.service';
import { useRouter } from 'next/navigation';

export default function AdminPage() {
    const router = useRouter();
    const [user, setUser] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(false);
    const [fetchingProfile, setFetchingProfile] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    const [formData, setFormData] = useState({
        // Organization
        name: '',
        slug: '',
        country: 'US',
        egrid_subregion: '',
        // Initial Admin User
        admin_email: '',
        admin_password: '',
        admin_first_name: '',
        admin_last_name: '',
    });

    useEffect(() => {
        AuthService.getProfile()
            .then(setUser)
            .finally(() => setFetchingProfile(false));
    }, []);

    const handleNameChange = (name: string) => {
        const slug = name.toLowerCase().replace(/ /g, '-').replace(/[^\w-]+/g, '');
        setFormData({ ...formData, name, slug });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setSuccess(false);

        try {
            await OrganizationService.registerWithAdmin(formData);
            setSuccess(true);
            // Reset form
            setFormData({
                name: '', slug: '', country: 'US', egrid_subregion: '',
                admin_email: '', admin_password: '', admin_first_name: '', admin_last_name: ''
            });
        } catch (err: any) {
            setError(err.message || 'Failed to register organization and admin');
        } finally {
            setLoading(false);
        }
    };

    if (fetchingProfile) return <div style={{ padding: '40px' }}>Loading admin portal...</div>;

    if (!user?.is_superuser) {
        return (
            <div style={{ padding: '40px', textAlign: 'center' }}>
                <h1 style={{ color: '#ef4444' }}>Access Denied</h1>
                <p style={{ color: 'var(--color-text-muted)' }}>Only system superusers can access the registration portal.</p>
                <button 
                    onClick={() => router.push('/dashboard')}
                    style={{ ...buttonStyle, width: 'auto', marginTop: '20px', padding: '10px 20px' }}
                >
                    Back to Dashboard
                </button>
            </div>
        );
    }

    return (
        <div style={{ padding: '40px', maxWidth: '900px' }}>
            <h1 style={{ color: 'var(--color-text-primary)', marginBottom: '8px' }}>System Administration</h1>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '32px' }}>
                Register new client organizations and create their initial administrator account.
            </p>

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                
                {/* Section 1: Organization Details */}
                <div style={sectionStyle}>
                    <h2 style={sectionTitleStyle}>1. Organization Details</h2>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                        <div style={inputGroupStyle}>
                            <label style={labelStyle}>Organization Name</label>
                            <input 
                                type="text"
                                value={formData.name}
                                onChange={(e) => handleNameChange(e.target.value)}
                                required
                                placeholder="e.g. Acme Corporation"
                                style={inputStyle}
                            />
                        </div>
                        <div style={inputGroupStyle}>
                            <label style={labelStyle}>URL Slug</label>
                            <input 
                                type="text"
                                value={formData.slug}
                                onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                                required
                                placeholder="acme-corp"
                                style={inputStyle}
                            />
                        </div>
                        <div style={inputGroupStyle}>
                            <label style={labelStyle}>Country (ISO Code)</label>
                            <input 
                                type="text"
                                value={formData.country}
                                onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                                required
                                maxLength={2}
                                style={inputStyle}
                            />
                        </div>
                        <div style={inputGroupStyle}>
                            <label style={labelStyle}>eGRID Subregion (Optional)</label>
                            <input 
                                type="text"
                                value={formData.egrid_subregion}
                                onChange={(e) => setFormData({ ...formData, egrid_subregion: e.target.value })}
                                placeholder="e.g. CAMX"
                                style={inputStyle}
                            />
                        </div>
                    </div>
                </div>

                {/* Section 2: Initial Admin User */}
                <div style={sectionStyle}>
                    <h2 style={sectionTitleStyle}>2. Initial Admin User</h2>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                        <div style={inputGroupStyle}>
                            <label style={labelStyle}>Email Address (Username)</label>
                            <input 
                                type="email"
                                value={formData.admin_email}
                                onChange={(e) => setFormData({ ...formData, admin_email: e.target.value })}
                                required
                                placeholder="admin@acme.com"
                                style={inputStyle}
                            />
                        </div>
                        <div style={inputGroupStyle}>
                            <label style={labelStyle}>Initial Password</label>
                            <input 
                                type="password"
                                value={formData.admin_password}
                                onChange={(e) => setFormData({ ...formData, admin_password: e.target.value })}
                                required
                                placeholder="••••••••"
                                style={inputStyle}
                            />
                        </div>
                        <div style={inputGroupStyle}>
                            <label style={labelStyle}>First Name</label>
                            <input 
                                type="text"
                                value={formData.admin_first_name}
                                onChange={(e) => setFormData({ ...formData, admin_first_name: e.target.value })}
                                required
                                placeholder="Jane"
                                style={inputStyle}
                            />
                        </div>
                        <div style={inputGroupStyle}>
                            <label style={labelStyle}>Last Name</label>
                            <input 
                                type="text"
                                value={formData.admin_last_name}
                                onChange={(e) => setFormData({ ...formData, admin_last_name: e.target.value })}
                                required
                                placeholder="Doe"
                                style={inputStyle}
                            />
                        </div>
                    </div>
                </div>

                {error && <div style={errorStyle}>{error}</div>}
                {success && <div style={successStyle}>Organization and Admin User registered successfully!</div>}

                <button 
                    type="submit" 
                    disabled={loading}
                    style={{
                        ...buttonStyle,
                        cursor: loading ? 'not-allowed' : 'pointer',
                        opacity: loading ? 0.7 : 1,
                    }}
                >
                    {loading ? 'Processing...' : 'Register Organization & Create Admin'}
                </button>
            </form>
        </div>
    );
}

const sectionStyle = {
    background: 'var(--color-navy-light)',
    border: '1px solid var(--color-border)',
    borderRadius: '16px',
    padding: '32px'
};

const sectionTitleStyle = {
    fontSize: '1.1rem',
    fontWeight: 600,
    marginBottom: '24px',
    color: 'var(--color-text-primary)'
};

const inputGroupStyle = {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px'
};

const labelStyle = {
    fontSize: '0.85rem',
    color: 'var(--color-text-secondary)'
};

const inputStyle = {
    background: 'var(--color-navy)',
    border: '1px solid var(--color-border)',
    borderRadius: '8px',
    padding: '10px 14px',
    color: 'var(--color-text-primary)',
    fontSize: '0.95rem',
    outline: 'none',
};

const buttonStyle = {
    background: 'var(--color-emerald)',
    color: '#080c14',
    border: 'none',
    padding: '16px',
    borderRadius: '12px',
    fontWeight: 700,
    fontSize: '1rem',
    transition: 'transform 0.1s',
};

const errorStyle = {
    padding: '12px',
    background: 'rgba(239,68,68,0.1)',
    border: '1px solid rgba(239,68,68,0.2)',
    color: '#ef4444',
    borderRadius: '8px',
    fontSize: '0.9rem'
};

const successStyle = {
    padding: '12px',
    background: 'rgba(0,232,122,0.1)',
    border: '1px solid rgba(0,232,122,0.2)',
    color: 'var(--color-emerald)',
    borderRadius: '8px',
    fontSize: '0.9rem'
};
