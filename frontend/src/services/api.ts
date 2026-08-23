import axios from 'axios';
import type { DatasetResponse, PlanResult } from '../types';

/**
 * Base URL for the Atlas Fresh FastAPI backend.
 * Falls back to localhost:8000 for standard local development.
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache',
    Pragma: 'no-cache',
  },
  timeout: 10000,
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
