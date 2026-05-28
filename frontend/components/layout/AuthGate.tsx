'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getAuthToken } from '@/lib/api';

export default function AuthGate({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const [ready, setReady] = useState(false);

    useEffect(() => {
        if (!getAuthToken()) {
            router.replace('/');
            return;
        }

        setReady(true);
    }, [router]);

    if (!ready) {
        return (
            <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                Loading workspace…
            </div>
        );
    }

    return children;
}