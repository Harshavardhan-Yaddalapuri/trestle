/** Lifecycle values from `backend/schemas/grant_association.py` (closing-v1). */
export const GRANT_LIFECYCLE_STATUSES = [
  "interested",
  "researching",
  "drafting",
  "submitted",
  "under_review",
  "awarded",
  "rejected",
  "withdrawn",
  "abandoned",
] as const;

export type GrantLifecycleStatus = (typeof GRANT_LIFECYCLE_STATUSES)[number];

export const TERMINAL_GRANT_LIFECYCLE_STATUSES = [
  "awarded",
  "rejected",
  "withdrawn",
  "abandoned",
] as const;

export type TerminalGrantLifecycleStatus =
  (typeof TERMINAL_GRANT_LIFECYCLE_STATUSES)[number];

/** Non-terminal statuses — default for `GET /api/grants/lifecycle` with no filter. */
export const ACTIVE_GRANT_LIFECYCLE_STATUSES = GRANT_LIFECYCLE_STATUSES.filter(
  (s): s is Exclude<GrantLifecycleStatus, TerminalGrantLifecycleStatus> =>
    !(TERMINAL_GRANT_LIFECYCLE_STATUSES as readonly string[]).includes(s),
);

export function isGrantLifecycleStatus(
  value: string | undefined,
): value is GrantLifecycleStatus {
  return (
    value !== undefined &&
    (GRANT_LIFECYCLE_STATUSES as readonly string[]).includes(value)
  );
}

/** Pipeline order for status-column sorting (early → late → terminal). */
export const LIFECYCLE_PIPELINE_ORDER: readonly GrantLifecycleStatus[] = [
  "interested",
  "researching",
  "drafting",
  "submitted",
  "under_review",
  "awarded",
  "rejected",
  "withdrawn",
  "abandoned",
];

export const GRANT_LIFECYCLE_LABELS: Record<GrantLifecycleStatus, string> = {
  interested: "Interested",
  researching: "Researching",
  drafting: "Drafting",
  submitted: "Submitted",
  under_review: "Under review",
  awarded: "Awarded",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
  abandoned: "Abandoned",
};
