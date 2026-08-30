import type { ProfileOut } from "@/lib/api";

export type ProfileReadiness = {
  completed: number;
  total: number;
  percent: number;
  missingBasics: string[];
  grantsReady: boolean;
  eventsReady: boolean;
  alertsReady: boolean;
};

type ReadinessField = {
  label: string;
  present: (profile: ProfileOut) => boolean;
};

const BASIC_FIELDS: ReadinessField[] = [
  { label: "company name", present: (profile) => Boolean(profile.company_name?.trim()) },
  { label: "company stage", present: (profile) => Boolean(profile.company_stage) },
  { label: "industry", present: (profile) => Boolean(profile.industry?.length) },
  { label: "operating location", present: (profile) => Boolean(profile.location?.trim()) },
  { label: "team size", present: (profile) => profile.team_size !== null },
  { label: "one-line description", present: (profile) => Boolean(profile.one_liner?.trim()) },
  { label: "goals", present: (profile) => Boolean(profile.goals?.trim()) },
];

/** Shared recommendation-readiness rules for profile and onboarding surfaces. */
export function getProfileReadiness(profile: ProfileOut): ProfileReadiness {
  const completed = BASIC_FIELDS.filter((field) => field.present(profile)).length;
  const missingBasics = BASIC_FIELDS
    .filter((field) => !field.present(profile))
    .map((field) => field.label);

  const hasCoreMatchFields = Boolean(
    profile.company_stage && profile.industry?.length && profile.location?.trim()
  );

  return {
    completed,
    total: BASIC_FIELDS.length,
    percent: Math.round((completed / BASIC_FIELDS.length) * 100),
    missingBasics,
    grantsReady: hasCoreMatchFields && profile.incorporated !== null,
    eventsReady: hasCoreMatchFields && Boolean(profile.goals?.trim()),
    alertsReady: Boolean(profile.company_stage && (profile.location?.trim() || profile.incorporation_country)),
  };
}

export function blankProfile(): ProfileOut {
  return {
    session_id: "",
    user_id: null,
    founder_name: null,
    company_name: null,
    company_stage: null,
    industry: [],
    location: null,
    website: null,
    one_liner: null,
    goals: null,
    team_size: null,
    has_technical_cofounder: null,
    funding_raised_usd_cents: null,
    funding_target_usd_cents: null,
    incorporated: null,
    incorporation_country: null,
    incorporation_state: null,
    regulatory_status: {},
    created_at: null,
    updated_at: null,
  };
}
