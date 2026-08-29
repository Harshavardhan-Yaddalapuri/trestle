import { ApiError } from "@/lib/api-error";

export { ApiError };

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  params?: Record<string, string>;
};

export async function getAuthHeaders(): Promise<Record<string, string>> {
  if (typeof window === "undefined") return {};
  try {
    const { supabase } = await import("@/lib/supabase-client");
    const { data, error } = await supabase.auth.getSession();
    if (error) {
      console.warn("[getAuthHeaders] getSession error:", error.message);
      return {};
    }
    const token = data.session?.access_token;
    if (token) {
      return { Authorization: `Bearer ${token}` };
    }
  } catch (err) {
    console.warn("[getAuthHeaders] exception:", err);
  }
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
    credentials: "include",
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

/* ═══════════════════════════════════════════════════════════════
   TypeScript Interfaces (from API_SCHEMA_DESIGN.md §10)
   ═══════════════════════════════════════════════════════════════ */

export interface HealthResponse {
  status: string;
  service?: string;
}

export interface ProfileIn {
  founder_name?: string | null;
  company_name?: string | null;
  company_stage?: string | null;
  industry?: string[] | null;
  location?: string | null;
  website?: string | null;
  one_liner?: string | null;
  goals?: string | null;
  team_size?: number | null;
  has_technical_cofounder?: boolean | null;
  funding_raised_usd_cents?: number | null;
  funding_target_usd_cents?: number | null;
  incorporated?: boolean | null;
  incorporation_country?: string | null;
  incorporation_state?: string | null;
  regulatory_status?: Record<string, unknown> | null;
}

export interface ProfileOut {
  session_id: string;
  user_id: string | null;
  founder_name: string | null;
  company_name: string | null;
  company_stage: string | null;
  industry: string[] | null;
  location: string | null;
  website: string | null;
  one_liner: string | null;
  goals: string | null;
  team_size: number | null;
  has_technical_cofounder: boolean | null;
  funding_raised_usd_cents: number | null;
  funding_target_usd_cents: number | null;
  incorporated: boolean | null;
  incorporation_country: string | null;
  incorporation_state: string | null;
  regulatory_status: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
}

export interface AlertPreferences {
  deadline_reminders: boolean;
  new_grant_matches: boolean;
  check_ins: boolean;
}

export interface ChatMessageIn {
  conversation_id?: string | null;
  content: string;
}

export type SSEEventType =
  | "job_started"
  | "token"
  | "tool_call"
  | "tool_result"
  | "question_suggested"
  | "message_saved"
  | "error"
  | "done";

export interface SSEEvent<T = unknown> {
  event: SSEEventType;
  data: T;
}

export interface JobStartedData {
  job_id: string;
  conversation_id: string;
  created_at: string;
}

export interface TokenData {
  delta: string;
}

export interface ToolCallData {
  name: string;
  args: unknown;
}

export interface ToolResultData {
  name: string;
  result: unknown;
}

export interface QuestionSuggestedData {
  field: string;
  question: string;
  options?: string[];
}

export interface MessageSavedData {
  message_id: string;
  role: string;
  content: string;
  created_at: string;
}

export interface ErrorData {
  code: string;
  message: string;
}

export interface DoneData {
  finish_reason: string;
}

/* ── Grant ── */

export interface GrantSummary {
  id: string;
  source_id: string;
  name: string;
  type: "grant" | "contest" | "accelerator" | "fellowship" | "other";
  provider_name: string;
  deadline: string | null;
  rolling: boolean;
  amount_min: number | null;
  amount_max: number | null;
  amount_display: string;
  stage: string[] | null;
  industry: string[] | null;
  location: string[] | null;
  status: "active" | "expired" | "archived";
}

export interface GrantDetail extends GrantSummary {
  description: string;
  url: string;
  application_url: string | null;
  eligibility: Record<string, unknown>;
  provider_type: string | null;
  last_verified_at: string | null;
  source_status: string;
  created_at: string;
  updated_at: string;
}

export interface GrantCardData {
  name: string;
  amount: string;
  deadline: string;
  daysLeft?: number;
  eligibility: string;
  sourceUrl: string;
  freshness: "Verified this week" | "Verified recently" | "Needs verification";
  description?: string;
  budgetInfo?: string;
  eligibilityCriteria?: string[];
}

export function mapGrantToCard(grant: GrantSummary): GrantCardData {
  // Compute days-left from ISO deadline
  let daysLeft: number | undefined;
  let deadlineLabel = "No deadline";
  if (grant.deadline) {
    const d = new Date(grant.deadline);
    const now = new Date();
    const diff = Math.ceil((d.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    daysLeft = diff;
    deadlineLabel = d.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }

  return {
    name: grant.name,
    amount: grant.amount_display,
    deadline: deadlineLabel,
    daysLeft,
    eligibility: `Grant type: ${grant.type}. ${grant.provider_name}`,
    sourceUrl: `https://trestle.io/grants/${grant.source_id}`,
    freshness: "Verified recently",
  };
}

/* ── Match ── */

export interface MatchResult {
  grant: GrantSummary;
  score: number;
  tier: "strong" | "moderate" | "weak" | "ineligible";
  matched_on: string[];
  missing_or_mismatched: string[];
  hard_fails: Array<{ rule: string; code: string; detail: string }>;
  explanation: string;
  tracked: boolean;
  dismissed: boolean;
}

export interface MatchRequest {
  stage?: string | null;
  industry?: string[] | null;
  location?: string | null;
  limit?: number;
  min_score?: number;
  include_ineligible?: boolean;
  include_dismissed?: boolean;
}

/* ── Conversation ── */

export interface ConversationSummary {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message_preview: string | null;
}

export interface ConversationDetail extends ConversationSummary {
  messages: Array<{
    id: string;
    role: "user" | "assistant" | "system" | "tool";
    content: string;
    metadata: Record<string, unknown>;
    created_at: string;
  }>;
}

/* ── Pagination ── */

export interface PaginatedList<T> {
  items: T[];
  next_cursor: string | null;
}

/* ═══════════════════════════════════════════════════════════════
   Typed API Client
   ═══════════════════════════════════════════════════════════════ */

export const apiClient = {
  // Health
  health: () => request<HealthResponse>("/health"),

  // Profile
  getProfile: () => request<ProfileOut>("/api/users/profile"),

  updateProfile: (data: ProfileIn) =>
    request<ProfileOut>("/api/users/profile", {
      method: "PUT",
      body: data,
    }),

  getAlertPreferences: () =>
    request<AlertPreferences>("/api/users/alert-preferences"),

  updateAlertPreferences: (data: Partial<AlertPreferences>) =>
    request<AlertPreferences>("/api/users/alert-preferences", {
      method: "PUT",
      body: data,
    }),

  // Conversations
  listConversations: (params?: { limit?: string; cursor?: string }) =>
    request<PaginatedList<ConversationSummary>>("/api/conversations", { params }),

  getConversation: (id: string) =>
    request<ConversationDetail>(`/api/conversations/${id}`),

  deleteConversation: (id: string) =>
    request<void>(`/api/conversations/${id}`, { method: "DELETE" }),

  // Grants
  listGrants: (params?: {
    limit?: string;
    cursor?: string;
    type?: string;
    stage?: string;
    industry?: string;
    location?: string;
    status?: string;
    q?: string;
  }) => request<PaginatedList<GrantSummary>>("/api/grants", { params }),

  getGrant: (ref: string) => request<GrantDetail>(`/api/grants/${ref}`),

  matchGrants: (body: MatchRequest) =>
    request<{ match_profile: ProfileOut; results: MatchResult[]; total_evaluated: number; total_returned: number }>("/api/grants/match", {
      method: "POST",
      body,
    }),

  // Grant tracking
  trackGrant: (grant_id: string, note?: string) =>
    request<unknown>("/api/grants/track", { method: "POST", body: { grant_id, note } }),

  untrackGrant: (ref: string) =>
    request<void>(`/api/grants/track/${ref}`, { method: "DELETE" }),

  listTracked: (params?: { limit?: string; cursor?: string }) =>
    request<PaginatedList<{ id: string; grant: GrantSummary; note: string | null; created_at: string; updated_at: string }>>("/api/grants/tracked", { params }),

  // Grant dismissal
  dismissGrant: (grant_id: string, reason?: string) =>
    request<unknown>("/api/grants/dismiss", { method: "POST", body: { grant_id, reason } }),

  undismissGrant: (ref: string) =>
    request<void>(`/api/grants/dismiss/${ref}`, { method: "DELETE" }),

  listDismissed: (params?: { limit?: string; cursor?: string }) =>
    request<PaginatedList<unknown>>("/api/grants/dismissed", { params }),

  // Chat SSE stream
  chatStream: (
    body: ChatMessageIn,
    options: {
      onMessage: (event: SSEEvent) => void;
      onError?: (error: Error) => void;
      onOpen?: () => void;
      onClose?: () => void;
    },
  ): (() => void) => {
    const controller = new AbortController();

    (async () => {
      try {
        const authHeaders = await getAuthHeaders();
        const url = new URL("/api/chat/message", API_BASE);
        const res = await fetch(url.toString(), {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
            ...authHeaders,
          },
          body: JSON.stringify(body),
          signal: controller.signal,
          credentials: "include",
        });

        if (!res.ok) {
          const text = await res.text().catch(() => res.statusText);
          throw new Error(`SSE POST failed: ${res.status} — ${text}`);
        }

        options.onOpen?.();

        const reader = res.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          let currentEvent: SSEEventType = "token";
          let currentData = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              currentEvent = line.slice(7).trim() as SSEEventType;
            } else if (line.startsWith("data: ")) {
              currentData += line.slice(6);
            } else if (line === "") {
              if (currentData) {
                try {
                  const parsed = JSON.parse(currentData);
                  options.onMessage({ event: currentEvent, data: parsed });
                } catch {
                  options.onMessage({ event: currentEvent, data: currentData });
                }
                currentEvent = "token";
                currentData = "";
              }
            }
          }
        }

        options.onClose?.();
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          options.onError?.(err as Error);
        }
      }
    })();

    return () => controller.abort();
  },

  /** Resume an interrupted stream using a known job_id.
   *  Not currently wired into the UI but exposed for future reconnect logic.
   */
  resumeChatStream: (
    jobId: string,
    lastEventId: string,
    options: {
      onMessage: (event: SSEEvent) => void;
      onError?: (error: Error) => void;
      onOpen?: () => void;
      onClose?: () => void;
    },
  ): (() => void) => {
    const controller = new AbortController();

    (async () => {
      try {
        const authHeaders = await getAuthHeaders();
        const url = new URL(`/api/chat/stream/${jobId}`, API_BASE);
        const res = await fetch(url.toString(), {
          headers: {
            Accept: "text/event-stream",
            "Last-Event-ID": lastEventId,
            ...authHeaders,
          },
          signal: controller.signal,
          credentials: "include",
        });

        if (!res.ok) {
          const text = await res.text().catch(() => res.statusText);
          throw new Error(`Resume failed: ${res.status} — ${text}`);
        }

        options.onOpen?.();

        const reader = res.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          let currentEvent: SSEEventType = "token";
          let currentData = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              currentEvent = line.slice(7).trim() as SSEEventType;
            } else if (line.startsWith("data: ")) {
              currentData += line.slice(6);
            } else if (line === "") {
              if (currentData) {
                try {
                  const parsed = JSON.parse(currentData);
                  options.onMessage({ event: currentEvent, data: parsed });
                } catch {
                  options.onMessage({ event: currentEvent, data: currentData });
                }
                currentEvent = "token";
                currentData = "";
              }
            }
          }
        }

        options.onClose?.();
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          options.onError?.(err as Error);
        }
      }
    })();

    return () => controller.abort();
  },
};
