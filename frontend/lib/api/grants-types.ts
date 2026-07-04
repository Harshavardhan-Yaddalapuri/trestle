/** Types aligned with `backend/schemas/grant.py` and `grant_association.py`. */

export type GrantLifecycleStatus =
  | "interested"
  | "researching"
  | "drafting"
  | "submitted"
  | "under_review"
  | "awarded"
  | "rejected"
  | "withdrawn"
  | "abandoned";

export interface ApiGrantSummary {
  id: string;
  source_id: string;
  name: string;
  type: string;
  provider_name: string;
  deadline: string | null;
  rolling: boolean;
  amount_min: number | null;
  amount_max: number | null;
  stage: string[] | null;
  industry: string[] | null;
  location: string[] | null;
  status: string;
  amount_display: string;
}

export interface ApiGrantTrackOut {
  id: string;
  grant: ApiGrantSummary;
  note: string | null;
  created_at: string;
  updated_at: string;
  lifecycle_status: GrantLifecycleStatus;
  lifecycle_updated_at: string;
  lifecycle_metadata: Record<string, unknown>;
}

export interface ApiGrantLifecycleListResponse {
  items: ApiGrantTrackOut[];
  next_cursor: string | null;
}

export interface ApiGrantDetail {
  id: string;
  source_id: string;
  name: string;
  type: string;
  description: string;
  url: string;
  application_url: string | null;
  amount_min: number | null;
  amount_max: number | null;
  deadline: string | null;
  rolling: boolean;
  stage: string[] | null;
  industry: string[] | null;
  location: string[] | null;
  eligibility: Record<string, unknown>;
  provider_name: string;
  provider_type: string | null;
  status: string;
  amount_display: string;
}

export interface ApiGrantLifecycleEventOut {
  id: string;
  from_status: GrantLifecycleStatus | null;
  to_status: GrantLifecycleStatus;
  transition_kind: "user" | "automated" | "system";
  note: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ApiGrantLifecycleEventListResponse {
  events: ApiGrantLifecycleEventOut[];
}
