import { request } from './api.client';
import { PaginatedResponse } from '../lib/api';

export interface Organization {
    id: string;
    name: string;
    slug: string;
    egrid_subregion: string;
    country: string;
    is_active: boolean;
    member_count?: number;
    facility_count?: number;
    created_at: string;
    updated_at: string;
}

export interface UserOrganization {
    id: string;
    user: string;
    user_email: string;
    user_name: string;
    organization: string;
    organization_name: string;
    role: 'admin' | 'analyst' | 'viewer';
    role_display: string;
    invited_by: string;
    created_at: string;
}

export const OrganizationService = {
    /**
     * List all organizations the current user belongs to.
     */
    getOrganizations: (params?: Record<string, string>) => {
        const qs = params ? '?' + new URLSearchParams(params).toString() : '';
        return request<PaginatedResponse<Organization>>(`/organizations/${qs}`);
    },

    /**
     * Create a new organization.
     */
    createOrganization: (data: Partial<Organization>) => {
        return request<Organization>('/organizations/', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    /**
     * Create a new organization and its initial admin user in one go.
     */
    registerWithAdmin: (data: any) => {
        return request<any>('/organizations/register_with_admin/', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    /**
     * Retrieve a specific organization by ID.
     */
    getOrganization: (id: string) => {
        return request<Organization>(`/organizations/${id}/`);
    },

    /**
     * Update an organization's details.
     */
    updateOrganization: (id: string, data: Partial<Organization>) => {
        return request<Organization>(`/organizations/${id}/`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    },

    /**
     * Soft-delete an organization.
     */
    deleteOrganization: (id: string) => {
        return request(`/organizations/${id}/`, {
            method: 'DELETE',
        });
    },

    /**
     * Add a member to an organization by email. Creates account if needed.
     */
    inviteMemberByEmail: (orgId: string, data: { email: string; role: string; first_name?: string; last_name?: string }) => {
        return request<any>(`/organizations/${orgId}/invite_member/`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    /**
     * List members of an organization.
     */
    getMembers: (orgId: string) => {
        return request<UserOrganization[]>(`/organizations/${orgId}/members/`);
    },

    /**
     * Add a member to an organization.
     */
    addMember: (orgId: string, data: { user: string; role: string }) => {
        return request<UserOrganization>(`/organizations/${orgId}/members/`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },
};
