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

export const EVENT_DEMO_PROFILE_OPTIONS = [
  "none",
  "ai_seed_founder",
  "biotech_founder",
  "climate_operator",
] as const;
export type EventDemoProfileOption = (typeof EVENT_DEMO_PROFILE_OPTIONS)[number];

export const EVENT_DEMO_PROFILE_LABELS: Record<EventDemoProfileOption, string> = {
  none: "None (all events)",
  ai_seed_founder: "AI founder (seed)",
  biotech_founder: "Biotech founder (pre-seed)",
  climate_operator: "Climate founder (Series A+)",
};

export interface EventsListQuery {
  profile?: EventDemoProfileOption;
}

export function parseEventsListQuery(searchParams: {
  profile?: string;
}): EventsListQuery {
  const profile = EVENT_DEMO_PROFILE_OPTIONS.includes(
    searchParams.profile as EventDemoProfileOption,
  )
    ? (searchParams.profile as EventDemoProfileOption)
    : undefined;
  return { profile };
}

export function buildEventsListHref(query: EventsListQuery): string {
  const params = new URLSearchParams();
  if (query.profile && query.profile !== "none") params.set("profile", query.profile);
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
