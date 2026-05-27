const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
    message?: string,
  ) {
    super(message || `API error ${status}`);
    this.name = "ApiError";
  }
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  params?: Record<string, string>;
};

async function getAuthHeaders(): Promise<Record<string, string>> {
  // Stub — inject auth token here once auth is wired up
  return {};
}

async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { body, params, headers: extraHeaders, ...rest } = options;

  const url = new URL(path, API_BASE);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }

  const authHeaders = await getAuthHeaders();

  const res = await fetch(url.toString(), {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...(extraHeaders as Record<string, string>),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let errorBody: unknown;
    try {
      errorBody = await res.json();
    } catch {
      errorBody = await res.text();
    }
    throw new ApiError(res.status, errorBody, `${res.status} ${res.statusText}`);
  }

  const text = await res.text();
  return text ? (JSON.parse(text) as T) : (undefined as T);
}

/* ── Typed API methods ── */

export interface HealthResponse {
  status: string;
  service?: string;
}

export interface SearchRequest {
  query: string;
  limit?: number;
  profile_id?: string;
  session_id?: string;
}

export interface Resource {
  id: string;
  name: string;
  type: string;
  description: string | null;
  url: string | null;
  application_url: string | null;
  location: string[] | null;
  industry: string[] | null;
  stage: string[] | null;
  deadline: string | null;
  prize_amount: string | null;
  funding_range: string | null;
  eligibility: Record<string, unknown> | null;
  status: string;
  updated_at: string | null;
}

export interface FitResult {
  resource: Resource;
  fit_explanation: string;
  next_step: string;
  confidence_badge: string;
  fit_score: number;
}

export interface SearchResponse {
  query_parsed: {
    location: string | null;
    state: string | null;
    stage: string | null;
    need_type: string | null;
    timeline: string | null;
    industry: string[] | null;
    demographics: string[] | null;
    funding_range: string | null;
  };
  results: FitResult[];
  total_found: number;
  memory_used: string[] | null;
}

export interface ScoutStatus {
  last_run: string | null;
  next_run: string | null;
  is_running: boolean;
  runs_today: number;
}

export const apiClient = {
  health: () => request<HealthResponse>("/health"),

  search: (data: SearchRequest) =>
    request<SearchResponse>("/api/api/search", {
      method: "POST",
      body: data,
    }),

  scoutStatus: () => request<ScoutStatus>("/api/scout/status"),

  scoutRun: (query: string) =>
    request<unknown>("/api/scout/run", {
      method: "POST",
      body: { query },
    }),
};
