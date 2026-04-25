export type CaptureResult = {
  id: number;
  score: number | null;
  similarity_score: number | null;
  rerank_score: number | null;
  rank: number | null;
  timestamp: string;
  app_name: string;
  window_title: string | null;
  content: string;
  snippet: string;
  source_type: string;
  url: string | null;
  file_path: string | null;
  is_noise: number | null;
};

export type SearchResponse = {
  query: string;
  count: number;
  candidate_count: number;
  elapsed_ms: number;
  index_backend: string;
  reranker: string;
  results: CaptureResult[];
};

export type RecentResponse = {
  count: number;
  results: CaptureResult[];
};

export type StatsResponse = {
  database_path: string;
  total_captures: number;
  indexed_available: boolean;
  counts_by_app: Array<{ app_name: string; count: number }>;
  counts_by_source_type: Array<{ source_type: string; count: number }>;
  noise_counts: Array<{ is_noise: number | null; count: number }>;
  latest_capture_at: string | null;
};

export type HealthResponse = {
  ok: boolean;
  api_key_enabled: boolean;
};

export type PrivacySettings = {
  blocked_apps: string[];
  blocked_domains: string[];
  excluded_path_fragments: string[];
};

export type ClientConfig = {
  baseUrl: string;
  apiKey: string;
};

const jsonHeaders = (config: ClientConfig): HeadersInit => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (config.apiKey.trim()) {
    headers['X-MemoryOS-API-Key'] = config.apiKey.trim();
  }
  return headers;
};

async function request<T>(config: ClientConfig, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${config.baseUrl}${path}`, {
    ...init,
    headers: {
      ...jsonHeaders(config),
      ...(init?.headers || {}),
    },
  });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      const text = await response.text();
      if (text) message = text;
    }
    throw new Error(message);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: (config: ClientConfig) => request<HealthResponse>(config, '/health'),
  stats: (config: ClientConfig) => request<StatsResponse>(config, '/stats'),
  recent: (config: ClientConfig, limit = 50, appName = '', sourceType = '') => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (appName) params.set('app_name', appName);
    if (sourceType) params.set('source_type', sourceType);
    return request<RecentResponse>(config, `/recent?${params.toString()}`);
  },
  search: (config: ClientConfig, query: string, topK = 10) =>
    request<SearchResponse>(config, '/search', {
      method: 'POST',
      body: JSON.stringify({ query, top_k: topK }),
    }),
  refreshIndex: (config: ClientConfig, backend = 'auto') =>
    request<{ indexed_count: number; artifact_path: string; backend: string }>(config, '/refresh-index', {
      method: 'POST',
      body: JSON.stringify({ backend }),
    }),
  logClick: (config: ClientConfig, query: string, captureId: number, rank: number | null, dwellMs?: number) => {
    const params = new URLSearchParams({
      query,
      capture_id: String(captureId),
    });
    if (rank !== null) params.set('rank', String(rank));
    if (dwellMs !== undefined) params.set('dwell_ms', String(Math.max(0, Math.round(dwellMs))));
    return request<void>(config, `/click?${params.toString()}`, { method: 'POST' });
  },
  openCapture: (config: ClientConfig, captureId: number) =>
    request<{ opened: boolean; target: string }>(config, '/open', {
      method: 'POST',
      body: JSON.stringify({ capture_id: captureId }),
    }),
  labelNoise: (config: ClientConfig, captureId: number, isNoise: number | null) =>
    request<void>(config, `/captures/${captureId}/noise`, {
      method: 'PATCH',
      body: JSON.stringify({ is_noise: isNoise }),
    }),
  bulkLabelNoise: (config: ClientConfig, captureIds: number[], isNoise: number | null) =>
    request<{ updated_count: number }>(config, '/captures/noise/bulk', {
      method: 'PATCH',
      body: JSON.stringify({ capture_ids: captureIds, is_noise: isNoise }),
    }),
  privacy: (config: ClientConfig) => request<PrivacySettings>(config, '/privacy'),
  savePrivacy: (config: ClientConfig, settings: PrivacySettings) =>
    request<PrivacySettings>(config, '/privacy', {
      method: 'PUT',
      body: JSON.stringify(settings),
    }),
  exportData: (config: ClientConfig) => request<unknown>(config, '/export'),
  forget: (
    config: ClientConfig,
    body: { from_timestamp?: string; to_timestamp?: string; app_name?: string; source_type?: string; confirm: boolean },
  ) =>
    request<{ deleted_count: number }>(config, '/forget', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
};
