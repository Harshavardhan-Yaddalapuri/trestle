import type { GrantLifecycleStatus } from "@/lib/domain/lifecycle";
import type { TrackedGrantDetail, TrackedGrantSummary } from "@/lib/domain/tracked-grant";
import { MOCK_TRACKED_GRANTS } from "@/lib/data/mock/seed-data";

export interface ListTrackedGrantsFilter {
  status?: GrantLifecycleStatus;
}

function toSummary(d: TrackedGrantDetail): TrackedGrantSummary {
  return {
    id: d.id,
    catalogResourceId: d.catalogResourceId,
    name: d.name,
    status: d.status,
    amountLabel: d.amountLabel,
    deadlineLabel: d.deadlineLabel,
    deadlineIso: d.deadlineIso,
    updatedAt: d.updatedAt,
  };
}

export async function listTrackedGrants(
  filter: ListTrackedGrantsFilter = {},
): Promise<TrackedGrantSummary[]> {
  await Promise.resolve();
  const { status } = filter;
  const rows = status
    ? MOCK_TRACKED_GRANTS.filter((g) => g.status === status)
    : MOCK_TRACKED_GRANTS;
  return rows.map(toSummary);
}

export async function getTrackedGrantDetail(
  id: string,
): Promise<TrackedGrantDetail | null> {
  await Promise.resolve();
  return MOCK_TRACKED_GRANTS.find((g) => g.id === id) ?? null;
}
