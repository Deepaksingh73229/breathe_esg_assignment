'use client';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { clearAuthToken } from '@/lib/api';
import { useEffect, useState } from 'react';
import { AuthService, UserProfile } from '@/services/auth.service';

const BASE_NAV = [
    { href: '/dashboard', icon: GridIcon, label: 'Dashboard' },
    { href: '/facilities', icon: HomeIcon, label: 'Facilities' },
    { href: '/ingest', icon: UploadIcon, label: 'Ingest' },
    { href: '/review', icon: CheckIcon, label: 'Review' },
    { href: '/factors', icon: FlaskIcon, label: 'Factors' },
    { href: '/audit', icon: ShieldIcon, label: 'Audit Log' },
];

export default function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const [user, setUser] = useState<UserProfile | null>(null);

    useEffect(() => {
        AuthService.getProfile()
            .then(setUser)
            .catch(() => {
                // Not logged in or session expired
            });
    }, []);

    function handleLogout() {
        AuthService.logout();
    }

    const isOrgAdmin = user?.organizations.some(org => org.role === 'admin');
    
    const navItems = [...BASE_NAV];
    
    // Org Admins get a Settings page to manage members
    if (isOrgAdmin) {
        navItems.push({ href: '/settings', icon: SettingsIcon, label: 'Settings' });
    }

    // Only System Superadmins get the Admin registration portal
    if (user?.is_superuser) {
        navItems.push({ href: '/admin', icon: LockIcon, label: 'Admin' });
    }

    navItems.push({ href: '/profile', icon: UserIcon, label: 'Profile' });

    return (
        <aside style={{
            width: '72px',
            minHeight: '100vh',
            background: 'var(--color-navy)',
            borderRight: '1px solid var(--color-border)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            padding: '20px 0',
            gap: '4px',
            position: 'fixed',
            left: 0,
            top: 0,
            bottom: 0,
            zIndex: 50,
        }}>
            {/* Logo mark */}
            <Link href="/dashboard" style={{ textDecoration: 'none', marginBottom: '24px' }}>
                <div style={{
                    width: '40px', height: '40px', borderRadius: '12px',
                    background: 'var(--color-emerald)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    boxShadow: '0 0 20px rgba(0,232,122,0.3)',
                    transition: 'box-shadow 0.2s',
                }}>
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="9" fill="#080c14" opacity="0.3" />
                        <path d="M7 13l3 3 7-7" stroke="#080c14" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                </div>
            </Link>

            {/* Nav items */}
            <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1, width: '100%', padding: '0 10px' }}>
                {navItems.map(({ href, icon: Icon, label }) => {
                    const active = pathname === href || pathname.startsWith(href + '/');
                    return (
                        <Link key={href} href={href} title={label} style={{ textDecoration: 'none' }}>
                            <div style={{
                                width: '52px', height: '52px', borderRadius: '14px',
                                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                                gap: '3px',
                                background: active ? 'rgba(0,232,122,0.12)' : 'transparent',
                                border: `1px solid ${active ? 'rgba(0,232,122,0.25)' : 'transparent'}`,
                                color: active ? 'var(--color-emerald)' : 'var(--color-text-muted)',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                            }}
                                onMouseEnter={e => { if (!active) { (e.currentTarget as HTMLDivElement).style.background = 'var(--color-slate)'; (e.currentTarget as HTMLDivElement).style.color = 'var(--color-text-secondary)'; } }}
                                onMouseLeave={e => { if (!active) { (e.currentTarget as HTMLDivElement).style.background = 'transparent'; (e.currentTarget as HTMLDivElement).style.color = 'var(--color-text-muted)'; } }}
                            >
                                <Icon size={18} />
                                <span style={{ fontSize: '0.55rem', fontFamily: 'var(--font-mono)', letterSpacing: '0.02em', fontWeight: 500 }}>
                                    {label.toUpperCase().slice(0, 3)}
                                </span>
                            </div>
                        </Link>
                    );
                })}
            </nav>

            {/* Logout */}
            <button onClick={handleLogout} title="Sign out" style={{
                width: '52px', height: '52px', borderRadius: '14px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'transparent', border: 'none', cursor: 'pointer',
                color: 'var(--color-text-muted)',
                transition: 'all 0.2s',
                marginTop: 'auto',
            }}
                onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = '#ef4444'; (e.currentTarget as HTMLButtonElement).style.background = 'rgba(239,68,68,0.08)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--color-text-muted)'; (e.currentTarget as HTMLButtonElement).style.background = 'transparent'; }}
            >
                <LogOutIcon size={18} />
            </button>
        </aside>
    );
}

// ── Icon components ───────────────────────────────────────────────────────────
function GridIcon({ size = 20 }: { size?: number }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" />
        </svg>
    );
}
function HomeIcon({ size = 20 }: { size?: number }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
            <polyline points="9 22 9 12 15 12 15 22" />
        </svg>
    );
}
function UploadIcon({ size = 20 }: { size?: number }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
        </svg>
    );
}
function CheckIcon({ size = 20 }: { size?: number }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
        </svg>
    );
}
function FlaskIcon({ size = 20 }: { size?: number }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v11l-7 7h20l-7-7V3" />
        </svg>
    );
}
function ShieldIcon({ size = 20 }: { size?: number }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
    );
}
function LockIcon({ size = 20 }: { size?: number }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
    );
}
function UserIcon({ size = 20 }: { size?: number }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
        </svg>
    );
}
function SettingsIcon({ size = 20 }: { size?: number }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
    );
}
function LogOutIcon({ size = 20 }: { size?: number }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
        </svg>
    );
}