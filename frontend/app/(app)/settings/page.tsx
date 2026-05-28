'use client';

import React, { useState, useEffect, CSSProperties } from 'react';
import { OrganizationService } from '@/services/organization.service';
import { AuthService, UserProfile } from '@/services/auth.service';

export default function SettingsPage() {
    const [members, setMembers] = useState<any[]>([]);
    const [user, setUser] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [inviteEmail, setInviteEmail] = useState('');
    const [inviteRole, setInviteRole] = useState('viewer');

    useEffect(() => {
        const fetchData = async () => {
            try {
                const profile = await AuthService.getProfile();
                setUser(profile);
                
                if (profile.organizations.length > 0) {
                    const orgId = profile.organizations[0].id;
                    const membersRes = await OrganizationService.getMembers(orgId);
                    setMembers(membersRes || []);
                }
            } catch (err) {
                console.error('Failed to load settings', err);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const handleInvite = async (e: React.FormEvent) => {
        e.preventDefault();
        const orgId = user?.organizations?.[0]?.id;
        if (!orgId) return;

        try {
            await OrganizationService.inviteMemberByEmail(orgId, { email: inviteEmail, role: inviteRole });
            alert('Invitation sent successfully');
            setInviteEmail('');
            // Refresh members
            const updated = await OrganizationService.getMembers(orgId);
            setMembers(updated || []);
        } catch (err: any) {
            alert(err.message || 'Failed to send invitation');
        }
    };

    if (loading) return <div style={{ padding: '40px' }}>Loading settings...</div>;

    const currentOrg = user?.organizations?.[0];

    return (
        <div style={{ padding: '40px', maxWidth: '1000px' }}>
            <h1 style={{ color: 'var(--color-text-primary)', marginBottom: '32px' }}>Organization Settings</h1>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: '40px' }}>
                
                {/* Left Column: Team Management */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                    
                    <div style={cardStyle}>
                        <h2 style={cardTitleStyle}>General Settings</h2>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                            <div>
                                <label style={labelStyle}>Organization Name</label>
                                <div style={{ marginTop: '8px', color: '#fff', fontWeight: 600 }}>{currentOrg?.name}</div>
                            </div>
                            <div>
                                <label style={labelStyle}>Organization ID</label>
                                <div style={{ marginTop: '8px', color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>{currentOrg?.id}</div>
                            </div>
                        </div>
                    </div>

                    <div style={cardStyle}>
                        <h2 style={cardTitleStyle}>Team Members</h2>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            {members.map(member => (
                                <div key={member.id} style={memberItemStyle}>
                                    <div>
                                        <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{member.performed_by_name || member.user_email || 'Member'}</div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{member.user_email}</div>
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                        <span style={{ 
                                            fontSize: '0.7rem', 
                                            background: 'rgba(255,255,255,0.05)', 
                                            padding: '4px 8px', 
                                            borderRadius: '4px',
                                            textTransform: 'uppercase'
                                        }}>
                                            {member.role}
                                        </span>
                                        {user?.is_superuser && (
                                            <button style={{ background: 'none', border: 'none', color: '#ef4444', fontSize: '0.75rem', cursor: 'pointer' }}>Remove</button>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Right Column: Invite */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                    <div style={cardStyle}>
                        <h2 style={cardTitleStyle}>Invite Member</h2>
                        <form onSubmit={handleInvite} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            <div style={inputGroupStyle}>
                                <label style={labelStyle}>Email Address</label>
                                <input 
                                    type="email"
                                    value={inviteEmail}
                                    onChange={(e) => setInviteEmail(e.target.value)}
                                    required
                                    placeholder="colleague@company.com"
                                    style={inputStyle}
                                />
                            </div>
                            <div style={inputGroupStyle}>
                                <label style={labelStyle}>Role</label>
                                <select 
                                    value={inviteRole}
                                    onChange={(e) => setInviteRole(e.target.value)}
                                    style={inputStyle}
                                >
                                    <option value="viewer">Viewer (Read-only)</option>
                                    <option value="analyst">Analyst (Data entry)</option>
                                    <option value="admin">Admin (Full access)</option>
                                </select>
                            </div>
                            <button type="submit" style={buttonStyle}>Send Invitation</button>
                        </form>
                    </div>

                    <div style={{ 
                        padding: '20px', 
                        background: 'rgba(245,158,11,0.05)', 
                        border: '1px solid rgba(245,158,11,0.2)', 
                        borderRadius: '16px',
                        color: '#f59e0b',
                        fontSize: '0.85rem'
                    }}>
                        <strong>Security Note:</strong> Invitations are sent immediately. New users must complete their profile using the link sent to their email.
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
    padding: '24px'
};

const cardTitleStyle: CSSProperties = {
    fontSize: '1rem',
    fontWeight: 600,
    marginBottom: '20px',
    color: 'var(--color-text-primary)'
};

const memberItemStyle: CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px',
    background: 'var(--color-navy)',
    border: '1px solid var(--color-border)',
    borderRadius: '10px'
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
    padding: '10px 12px',
    color: 'var(--color-text-primary)',
    fontSize: '0.9rem',
    outline: 'none',
};

const buttonStyle: CSSProperties = {
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
