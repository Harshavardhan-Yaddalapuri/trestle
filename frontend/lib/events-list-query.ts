export const EVENT_STAGE_OPTIONS = [
  "idea",
  "pre_seed",
  "seed",
  "series_a",
  "growth",
] as const;
export type EventStageOption = (typeof EVENT_STAGE_OPTIONS)[number];

export const EVENT_INDUSTRY_OPTIONS = [
  "ai",
  "health",
  "biotech",
  "fintech",
  "climate",
  "saas",
  "devtools",
] as const;
export type EventIndustryOption = (typeof EVENT_INDUSTRY_OPTIONS)[number];

export interface EventsListQuery {
  stage?: EventStageOption;
  industry?: EventIndustryOption;
  includeExpired?: boolean;
}

export function parseEventsListQuery(searchParams: {
  stage?: string;
  industry?: string;
  include_expired?: string;
}): EventsListQuery {
  const stage = EVENT_STAGE_OPTIONS.includes(searchParams.stage as EventStageOption)
    ? (searchParams.stage as EventStageOption)
    : undefined;
  const industry = EVENT_INDUSTRY_OPTIONS.includes(
    searchParams.industry as EventIndustryOption,
  )
    ? (searchParams.industry as EventIndustryOption)
    : undefined;
  const includeExpired =
    searchParams.include_expired === "1" || searchParams.include_expired === "true";
  return { stage, industry, includeExpired };
}

export function buildEventsListHref(query: EventsListQuery): string {
  const params = new URLSearchParams();
  if (query.stage) params.set("stage", query.stage);
  if (query.industry) params.set("industry", query.industry);
  if (query.includeExpired) params.set("include_expired", "1");
  const qs = params.toString();
  return qs ? `/events?${qs}` : "/events";
}

export const EVENT_STAGE_LABELS: Record<EventStageOption, string> = {
  idea: "Idea",
  pre_seed: "Pre-seed",
  seed: "Seed",
  series_a: "Series A",
  growth: "Growth",
};

export const EVENT_INDUSTRY_LABELS: Record<EventIndustryOption, string> = {
  ai: "AI",
  health: "Health",
  biotech: "Biotech",
  fintech: "Fintech",
  climate: "Climate",
  saas: "SaaS",
  devtools: "Devtools",
};
