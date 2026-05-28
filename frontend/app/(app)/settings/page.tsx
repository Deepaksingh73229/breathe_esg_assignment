'use client';

import React, { useState, useEffect } from 'react';
import { OrganizationService, Organization, UserOrganization } from '@/services/organization.service';
import { AuthService, UserProfile } from '@/services/auth.service';

export default function SettingsPage() {
    const [user, setUser] = useState<UserProfile | null>(null);
    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [selectedOrgId, setSelectedOrgId] = useState<string>('');
    const [members, setMembers] = useState<UserOrganization[]>([]);
    const [loading, setLoading] = useState(true);
    const [inviting, setInviting] = useState(false);
    
    // Invite member form
    const [inviteData, setInviteData] = useState({
        email: '',
        first_name: '',
        last_name: '',
        role: 'analyst' as const
    });

    useEffect(() => {
        const fetchData = async () => {
            try {
                const profile = await AuthService.getProfile();
                setUser(profile);
                
                const orgs = await OrganizationService.getOrganizations();
                setOrganizations(orgs.results);
                
                if (orgs.results.length > 0) {
                    setSelectedOrgId(orgs.results[0].id);
                }
            } catch (err) {
                console.error('Failed to load settings data', err);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    useEffect(() => {
        if (selectedOrgId) {
            OrganizationService.getMembers(selectedOrgId)
                .then(setMembers)
                .catch(console.error);
        }
    }, [selectedOrgId]);

    const handleInvite = async (e: React.FormEvent) => {
        e.preventDefault();
        setInviting(true);
        try {
            const result = await OrganizationService.inviteMemberByEmail(selectedOrgId, inviteData);
            
            // Refresh member list
            const updatedMembers = await OrganizationService.getMembers(selectedOrgId);
            setMembers(updatedMembers);
            
            setInviteData({ email: '', first_name: '', last_name: '', role: 'analyst' });
            
            let msg = 'Member invited successfully!';
            if (result.is_new_user) {
                msg += `\n\nA new account was created. Temporary password: ${result.temporary_password}`;
            }
            alert(msg);
        } catch (err: any) {
            alert(err.message || 'Failed to invite member');
        } finally {
            setInviting(false);
        }
    };

    if (loading) return <div style={{ padding: '40px' }}>Loading settings...</div>;

    const isAdmin = user?.is_superuser || user?.organizations.find(o => o.id === selectedOrgId)?.role === 'admin';

    return (
        <div style={{ padding: '40px', maxWidth: '1000px' }}>
            <h1 style={{ color: 'var(--color-text-primary)', marginBottom: '8px' }}>Organization Settings</h1>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '32px' }}>
                Manage your organization's members and configuration.
            </p>

            <div style={{ display: 'flex', gap: '24px', marginBottom: '32px' }}>
                <div style={{ flex: 1 }}>
                    <label style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', display: 'block', marginBottom: '8px' }}>
                        Select Organization
                    </label>
                    <select 
                        value={selectedOrgId} 
                        onChange={(e) => setSelectedOrgId(e.target.value)}
                        style={inputStyle}
                    >
                        {organizations.map(org => (
                            <option key={org.id} value={org.id}>{org.name}</option>
                        ))}
                    </select>
                </div>
                <div style={{ flex: 2 }}></div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '32px' }}>
                {/* Member List */}
                <div style={cardStyle}>
                    <h2 style={cardTitleStyle}>Members</h2>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {members.map(member => (
                            <div key={member.id} style={memberItemStyle}>
                                <div>
                                    <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>{member.user_name}</div>
                                    <div style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>{member.user_email}</div>
                                </div>
                                <div style={{ 
                                    padding: '4px 10px', 
                                    borderRadius: '6px', 
                                    fontSize: '0.75rem', 
                                    fontWeight: 700,
                                    background: member.role === 'admin' ? 'rgba(0,232,122,0.1)' : 'rgba(255,255,255,0.05)',
                                    color: member.role === 'admin' ? 'var(--color-emerald)' : 'var(--color-text-secondary)',
                                    textTransform: 'uppercase'
                                }}>
                                    {member.role}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Invite Form */}
                <div style={{ ...cardStyle, opacity: isAdmin ? 1 : 0.5, pointerEvents: isAdmin ? 'auto' : 'none' }}>
                    <h2 style={cardTitleStyle}>Invite Member</h2>
                    {!isAdmin && <p style={{ fontSize: '0.8rem', color: '#ef4444', marginBottom: '16px' }}>Only admins can invite members.</p>}
                    <form onSubmit={handleInvite} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        <div style={inputGroupStyle}>
                            <label style={labelStyle}>Email Address</label>
                            <input 
                                type="email"
                                value={inviteData.email}
                                onChange={(e) => setInviteData({ ...inviteData, email: e.target.value })}
                                required
                                placeholder="jane@example.com"
                                style={inputStyle}
                            />
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                            <div style={inputGroupStyle}>
                                <label style={labelStyle}>First Name</label>
                                <input 
                                    type="text"
                                    value={inviteData.first_name}
                                    onChange={(e) => setInviteData({ ...inviteData, first_name: e.target.value })}
                                    placeholder="Jane"
                                    style={inputStyle}
                                />
                            </div>
                            <div style={inputGroupStyle}>
                                <label style={labelStyle}>Last Name</label>
                                <input 
                                    type="text"
                                    value={inviteData.last_name}
                                    onChange={(e) => setInviteData({ ...inviteData, last_name: e.target.value })}
                                    placeholder="Doe"
                                    style={inputStyle}
                                />
                            </div>
                        </div>
                        <div style={inputGroupStyle}>
                            <label style={labelStyle}>Role</label>
                            <select 
                                value={inviteData.role}
                                onChange={(e) => setInviteData({ ...inviteData, role: e.target.value as any })}
                                style={inputStyle}
                            >
                                <option value="analyst">Analyst (Data Ops)</option>
                                <option value="viewer">Viewer (Read-only)</option>
                                <option value="admin">Admin (Full Control)</option>
                            </select>
                        </div>
                        <button 
                            type="submit" 
                            disabled={inviting || !isAdmin}
                            style={buttonStyle}
                        >
                            {inviting ? 'Inviting...' : 'Send Invitation'}
                        </button>
                    </form>
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

const memberItemStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px',
    background: 'var(--color-navy)',
    border: '1px solid var(--color-border)',
    borderRadius: '10px'
};

const inputGroupStyle = {
    display: 'flex',
    flexDirection: 'column', gap: '6px'
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
    padding: '10px 12px',
    color: 'var(--color-text-primary)',
    fontSize: '0.9rem',
    outline: 'none',
};

const buttonStyle = {
    background: 'var(--color-emerald)',
    color: '#080c14',
    border: 'none',
    padding: '12px',
    borderRadius: '8px',
    fontWeight: 600,
    fontSize: '0.9rem',
    cursor: 'pointer',
    marginTop: '8px'
};
