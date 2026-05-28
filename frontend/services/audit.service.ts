import { request } from './api.client';
import { PaginatedResponse, AuditEntry } from '../lib/api';

export const AuditService = {
    getAuditLogs: (params?: Record<string, string>) => {
        const qs = params ? '?' + new URLSearchParams(params).toString() : '';
        return request<PaginatedResponse<AuditEntry>>(`/audit/${qs}`);
    },
};
