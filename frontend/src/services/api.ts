import axios from 'axios';
import type { AssistantResponse, DatasetResponse, PlanResult } from '../types';

/**
 * Derive the Base URL for the Atlas Fresh FastAPI backend.
 * Uses VITE_API_URL environment variable if set, or dynamically falls back
 * to the current browser hostname on port 8000 (e.g. http://localhost:8000).
 */
const getApiBaseUrl = (): string => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  if (typeof window !== 'undefined' && window.location && window.location.hostname) {
    const isLocalhost =
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1';
    if (isLocalhost) {
      return `http://${window.location.hostname}:8000`;
    }
    // In production (e.g. Vercel deployment), use relative origin so requests go to https://domain.com/api/...
    return '';
  }
  return '';
};

const apiClient = axios.create({
  baseURL: getApiBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache',
    Pragma: 'no-cache',
  },
  timeout: 12000,
});


/**
 * Fetch the complete daily export plan and executive KPIs from the planning engine.
 *
 * @returns {Promise<PlanResult>} Complete plan including KPIs, allocations, client statuses, and farm summaries.
 */
export async function fetchPlan(): Promise<PlanResult> {
  const response = await apiClient.get<PlanResult>('/api/plan', {
    params: { _t: Date.now() },
  });
  return response.data;
}

/**
 * Fetch the authoritative dataset containing farms, clients, and packing station configuration.
 *
 * @returns {Promise<DatasetResponse>} Full validated dataset.
 */
export async function fetchDataset(): Promise<DatasetResponse> {
  const response = await apiClient.get<DatasetResponse>('/api/data', {
    params: { _t: Date.now() },
  });
  return response.data;
}

/**
 * Query the Grounded AI Planning Assistant with operational questions.
 *
 * @param {string} query - Question or preset query string.
 * @returns {Promise<AssistantResponse>} Grounded answer, execution source, and cited IDs.
 */
export async function askAssistant(query: string): Promise<AssistantResponse> {
  const response = await apiClient.post<AssistantResponse>('/api/assistant/ask', {
    query,
  });
  return response.data;
}

