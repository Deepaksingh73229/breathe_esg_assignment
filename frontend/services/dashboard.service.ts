import { request } from './api.client';
import { DashboardSummary, TrendData, IngestionHealth, ReviewQueueResponse } from '../lib/api';

export const DashboardService = {
    getDashboardSummary: () => request<DashboardSummary>('/dashboard/summary/'),
    
    getDashboardTrends: (months = 6) =>
        request<TrendData>(`/dashboard/trends/?months=${months}`),
    
    getIngestionHealth: () => request<IngestionHealth>('/dashboard/ingestion_health/'),
    
    getReviewQueue: (params?: Record<string, string>) => {
        const qs = params ? '?' + new URLSearchParams(params).toString() : '';
        return request<ReviewQueueResponse>(`/dashboard/review_queue/${qs}`);
    },
};
