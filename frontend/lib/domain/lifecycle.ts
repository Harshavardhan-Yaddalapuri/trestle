export const GRANT_LIFECYCLE_STATUSES = [
  "saved",
  "applied",
  "under_review",
  "awarded",
  "rejected",
] as const;

export type GrantLifecycleStatus = (typeof GRANT_LIFECYCLE_STATUSES)[number];

export function isGrantLifecycleStatus(
  value: string | undefined,
): value is GrantLifecycleStatus {
  return (
    value !== undefined &&
    (GRANT_LIFECYCLE_STATUSES as readonly string[]).includes(value)
  );
}

export const GRANT_LIFECYCLE_LABELS: Record<GrantLifecycleStatus, string> = {
  saved: "Saved",
  applied: "Applied",
  under_review: "Under review",
  awarded: "Awarded",
  rejected: "Rejected",
};
