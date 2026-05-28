import { request } from './api.client';
import { PaginatedResponse, IngestionRun, IngestionResult } from '../lib/api';

export const IngestionService = {
    uploadFile: (formData: FormData) =>
        request<IngestionResult>('/ingestion/', { method: 'POST', body: formData }),
    
    getIngestionRuns: (params?: Record<string, string>) => {
        const qs = params ? '?' + new URLSearchParams(params).toString() : '';
        return request<PaginatedResponse<IngestionRun>>(`/ingestion/${qs}`);
    },
    
    getIngestionRun: (id: string) => request<IngestionRun>(`/ingestion/${id}/`),

    getIngestionRows: (id: string, params?: Record<string, string>) => {
        const qs = params ? '?' + new URLSearchParams(params).toString() : '';
        return request<PaginatedResponse<any>>(`/ingestion/${id}/rows/${qs}`);
    },

    getIngestionStatistics: (id: string) => 
        request<any>(`/ingestion/${id}/statistics/`),
};
