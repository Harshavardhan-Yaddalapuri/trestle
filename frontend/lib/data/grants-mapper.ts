import type { ApiGrantTrackOut } from "@/lib/api/grants-types";
import type { GrantLifecycleStatus } from "@/lib/domain/lifecycle";
import type { TrackedGrantSummary } from "@/lib/domain/tracked-grant";

function formatDeadline(deadline: string | null, rolling: boolean): {
  label: string | null;
  iso: string | null;
} {
  if (rolling && !deadline) {
    return { label: "Rolling", iso: null };
  }
  if (!deadline) {
    return { label: null, iso: null };
  }
  const d = new Date(`${deadline}T12:00:00`);
  if (Number.isNaN(d.getTime())) {
    return { label: deadline, iso: deadline };
  }
  return {
    label: d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    }),
    iso: deadline,
  };
}

export function mapGrantTrackToSummary(item: ApiGrantTrackOut): TrackedGrantSummary {
  const { grant } = item;
  const { label, iso } = formatDeadline(grant.deadline, grant.rolling);

  return {
    trackId: item.id,
    id: grant.source_id,
    grantId: grant.id,
    catalogResourceId: grant.source_id,
    name: grant.name,
    status: item.lifecycle_status as GrantLifecycleStatus,
    amountLabel: grant.amount_display ?? null,
    deadlineLabel: label,
    deadlineIso: iso,
    updatedAt: item.lifecycle_updated_at,
    providerName: grant.provider_name,
    grantType: grant.type,
  };
}
