import type { GrantLifecycleStatus } from "./lifecycle";

/** User-scoped tracking row from `GET /api/grants/lifecycle`. */
export interface TrackedGrantSummary {
  /** Grant catalog ref (`source_id`) — used in `/grants/[id]` URLs. */
  id: string;
  /** `GrantTrack` row id from the API. */
  trackId: string;
  /** Grant UUID from the API. */
  grantId: string;
  catalogResourceId: string | null;
  name: string;
  status: GrantLifecycleStatus;
  amountLabel: string | null;
  deadlineLabel: string | null;
  /** ISO date for sorting */
  deadlineIso: string | null;
  updatedAt: string;
  providerName?: string;
  grantType?: string;
}

export type TimelineEventKind =
  | "created"
  | "status_change"
  | "deadline"
  | "note"
  | "custom";

export interface GrantTimelineEvent {
  id: string;
  at: string;
  kind: TimelineEventKind;
  title: string;
  detail?: string;
}

export interface GrantNextStep {
  id: string;
  title: string;
  description?: string;
  dueDate?: string;
  done: boolean;
}

export interface GrantNote {
  id: string;
  body: string;
  authorLabel: string;
  createdAt: string;
}

export interface TrackedGrantDetail extends TrackedGrantSummary {
  description: string | null;
  eligibilitySummary: string | null;
  sourceUrl: string | null;
  applicationUrl: string | null;
  timeline: GrantTimelineEvent[];
  nextSteps: GrantNextStep[];
  notes: GrantNote[];
  /** Unknown keys from future API versions — rendered in an extension panel. */
  extensions?: Record<string, unknown>;
}
