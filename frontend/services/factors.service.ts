import { request } from './api.client';
import { PaginatedResponse, EmissionFactor } from '../lib/api';

export const FactorsService = {
    getFactors: (params?: Record<string, string>) => {
        const qs = params ? '?' + new URLSearchParams(params).toString() : '';
        return request<PaginatedResponse<EmissionFactor>>(`/factors/${qs}`);
    },
};
