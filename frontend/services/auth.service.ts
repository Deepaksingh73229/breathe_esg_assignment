import { request, setAuthToken, clearAuthToken } from './api.client';

export interface UserProfile {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    is_superuser: boolean;
    organizations: Array<{
        id: string;
        name: string;
        role: 'admin' | 'analyst' | 'viewer';
    }>;
}

export const AuthService = {
    login: async (username: string, password: string) => {
        const response = await request<{ token: string }>('/auth/login/', {
            method: 'POST',
            body: JSON.stringify({ username, password }),
        });
        if (response.token) {
            setAuthToken(response.token);
        }
        return response;
    },

    getProfile: () => request<UserProfile>('/organizations/me/'),

    updateProfile: (data: Partial<UserProfile>) => request<UserProfile>('/organizations/me/', {
        method: 'PATCH',
        body: JSON.stringify(data),
    }),

    logout: () => {
        clearAuthToken();
        if (typeof window !== 'undefined') {
            window.location.href = '/';
        }
    },
};
