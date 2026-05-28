import { request } from './api.client';
import { PaginatedResponse, ActivityRecord } from '../lib/api';

export const ActivitiesService = {
    getActivities: (params?: Record<string, string>) => {
        const qs = params ? '?' + new URLSearchParams(params).toString() : '';
        return request<PaginatedResponse<ActivityRecord>>(`/activities/${qs}`);
    },
    
    getActivity: (id: string) => request<ActivityRecord>(`/activities/${id}/`),
    
    approveActivity: (id: string, notes?: string) =>
        request(`/activities/${id}/approve/`, {
            method: 'POST',
            body: JSON.stringify({ notes: notes || '' }),
        }),
    
    rejectActivity: (id: string, notes?: string) =>
        request(`/activities/${id}/reject/`, {
            method: 'POST',
            body: JSON.stringify({ notes: notes || '' }),
        }),
    
    flagActivity: (id: string, notes?: string) =>
        request(`/activities/${id}/flag/`, {
            method: 'POST',
            body: JSON.stringify({ notes: notes || '' }),
        }),
    
    bulkReview: (ids: string[], action: string, notes?: string) =>
        request('/activities/bulk_review/', {
            method: 'POST',
            body: JSON.stringify({ ids, action, notes: notes || '' }),
        }),
    
    getAuditTrail: (id: string) => request(`/activities/${id}/audit_trail/`),

    editActivity: (id: string, data: Record<string, any>) =>
        request(`/activities/${id}/edit_record/`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }),
};
