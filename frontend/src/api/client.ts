import axios from 'axios';
import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';

// Types
export interface Project {
  id: number;
  name: string;
  project_id: string;
  created_at: string;
  updated_at: string;
  total_runs?: number;
  running_runs?: number;
  completed_runs?: number;
  failed_runs?: number;
}

export interface Run {
  id: number;
  project_id: number;
  run_id: string;
  name: string;
  group_name: string | null;
  state: 'running' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
}

export interface RunsListResponse {
  runs: Run[];
  total: number;
  has_more: boolean;
}

export interface MetricValue {
  step: number | null;
  timestamp: string | null;
  value: number | string | boolean;
}

export interface MetricValuesResponse {
  data: MetricValue[];
  has_more: boolean;
}

export interface RunFilters {
  project_id?: number;
  group?: string;
  state?: string;
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// API Client
const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// API functions
export const api = {
  // Projects
  getProjects: async (): Promise<Project[]> => {
    const { data } = await apiClient.get('/projects/');
    return data;
  },

  getProject: async (projectId: number): Promise<Project> => {
    const { data } = await apiClient.get(`/projects/${projectId}`);
    return data;
  },

  // Runs
  getRuns: async (filters: RunFilters & { limit?: number; offset?: number }): Promise<RunsListResponse> => {
    const { data } = await apiClient.get('/runs/', { params: filters });
    return data;
  },

  getRun: async (runId: number): Promise<Run> => {
    const { data } = await apiClient.get(`/runs/${runId}`);
    return data;
  },

  getRunSummary: async (runId: number) => {
    const { data } = await apiClient.get(`/runs/${runId}/summary`);
    return data;
  },

  // Metrics
  getRunMetrics: async (runId: number): Promise<string[]> => {
    const { data} = await apiClient.get(`/metrics/runs/${runId}`);
    return data;
  },

  getMetricValues: async (
    runId: number,
    metricPath: string,
    params?: { limit?: number; offset?: number; step_min?: number; step_max?: number }
  ): Promise<MetricValuesResponse> => {
    const { data } = await apiClient.get(`/metrics/runs/${runId}/metric/${metricPath}`, { params });
    return data;
  },

  compareMetrics: async (runIds: number[], metricPaths: string[]) => {
    const { data } = await apiClient.post('/metrics/compare', { run_ids: runIds, metric_paths: metricPaths });
    return data;
  },
};

// React Query Hooks
export function useProjects(options?: Omit<UseQueryOptions<Project[], Error>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: ['projects'],
    queryFn: api.getProjects,
    ...options,
  });
}

export function useProject(projectId: number, options?: Omit<UseQueryOptions<Project, Error>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: ['projects', projectId],
    queryFn: () => api.getProject(projectId),
    enabled: !!projectId,
    ...options,
  });
}

export function useRuns(
  filters: RunFilters,
  options?: Omit<UseQueryOptions<RunsListResponse, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: ['runs', filters],
    queryFn: () => api.getRuns({ ...filters, limit: 100 }),
    ...options,
  });
}

export function useInfiniteRuns(filters: RunFilters) {
  return useInfiniteQuery({
    queryKey: ['runs', 'infinite', filters],
    queryFn: ({ pageParam = 0 }) =>
      api.getRuns({ ...filters, limit: 50, offset: pageParam as number }),
    getNextPageParam: (lastPage, allPages) => {
      if (!lastPage.has_more) return undefined;
      return allPages.reduce((sum, page) => sum + page.runs.length, 0);
    },
    initialPageParam: 0,
  });
}

export function useRun(runId: number, options?: Omit<UseQueryOptions<Run, Error>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: ['runs', runId],
    queryFn: () => api.getRun(runId),
    enabled: !!runId,
    ...options,
  });
}

export function useRunSummary(runId: number, options?: Omit<UseQueryOptions<any, Error>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: ['runs', runId, 'summary'],
    queryFn: () => api.getRunSummary(runId),
    enabled: !!runId,
    ...options,
  });
}

export function useRunMetrics(runId: number, options?: Omit<UseQueryOptions<string[], Error>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: ['metrics', runId],
    queryFn: () => api.getRunMetrics(runId),
    enabled: !!runId,
    ...options,
  });
}

export function useMetricValues(
  runId: number,
  metricPath: string,
  options?: Omit<UseQueryOptions<MetricValuesResponse, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: ['metrics', runId, metricPath],
    queryFn: () => api.getMetricValues(runId, metricPath),
    enabled: !!runId && !!metricPath,
    ...options,
  });
}
