import { request } from './api.client';
import { PaginatedResponse, Facility } from '../lib/api';

export const FacilitiesService = {
    getFacilities: (params?: Record<string, string>) => {
        const qs = params ? '?' + new URLSearchParams(params).toString() : '';
        return request<PaginatedResponse<Facility>>(`/facilities/${qs}`);
    },
    getFacility: (id: string) => request<Facility>(`/facilities/${id}/`),
    
    createFacility: (data: Partial<Facility>) => 
        request<Facility>('/facilities/', {
            method: 'POST',
            body: JSON.stringify(data),
        }),
        
    updateFacility: (id: string, data: Partial<Facility>) =>
        request<Facility>(`/facilities/${id}/`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }),
        
    deleteFacility: (id: string) =>
        request(`/facilities/${id}/`, {
            method: 'DELETE',
        }),
};
