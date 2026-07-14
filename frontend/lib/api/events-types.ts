export interface ApiEventSummary {
  id: string;
  source_id: string;
  source: string;
  name: string;
  description: string;
  url: string;
  host_name: string | null;
  starts_at: string;
  ends_at: string | null;
  timezone: string | null;
  is_virtual: boolean;
  location_text: string | null;
  city: string | null;
  region: string | null;
  country: string | null;
  industry_tags: string[];
  stage_tags: string[];
  benefit_tags: string[];
  attendee_types: string[];
  cost_usd_cents: number | null;
  application_required: boolean;
  host_quality_score: number;
  status: "active" | "expired" | "archived" | string;
}

export interface ApiEventListResponse {
  items: ApiEventSummary[];
}
