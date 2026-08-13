import { fetchJson } from './client';
import type { HealthResponse } from '../types/health';

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return fetchJson<HealthResponse>('/api/v1/health', signal);
}
