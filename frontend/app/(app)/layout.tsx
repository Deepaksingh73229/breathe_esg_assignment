import AuthGate from '@/components/layout/AuthGate';
import Sidebar from '@/components/layout/Sidebar';

export default function AppLayout({ children }: { children: React.ReactNode }) {
    return (
        <AuthGate>
            <div style={{ display: 'flex', minHeight: '100vh' }}>
                <Sidebar />
                <main style={{ marginLeft: '72px', flex: 1, minHeight: '100vh', background: 'var(--color-obsidian)' }}>
                    {children}
                </main>
            </div>
        </AuthGate>
    );
}