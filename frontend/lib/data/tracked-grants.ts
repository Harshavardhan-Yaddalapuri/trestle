import { fetchGrantLifecycleList } from "@/lib/api/grants";
import { isMockDataSource } from "@/lib/config/data-source";
import type { GrantLifecycleStatus } from "@/lib/domain/lifecycle";
import type { TrackedGrantDetail, TrackedGrantSummary } from "@/lib/domain/tracked-grant";
import { mapGrantTrackToSummary } from "@/lib/data/grants-mapper";
import { MOCK_TRACKED_GRANTS } from "@/lib/data/mock/seed-data";

export interface ListTrackedGrantsFilter {
  status?: GrantLifecycleStatus;
  /** Include terminal lifecycle rows (awarded, rejected, …). */
  all?: boolean;
}

function toSummary(d: TrackedGrantDetail): TrackedGrantSummary {
  return {
    trackId: d.trackId,
    id: d.id,
    grantId: d.grantId,
    catalogResourceId: d.catalogResourceId,
    name: d.name,
    status: d.status,
    amountLabel: d.amountLabel,
    amountMin: d.amountMin,
    deadlineLabel: d.deadlineLabel,
    deadlineIso: d.deadlineIso,
    updatedAt: d.updatedAt,
    providerName: d.providerName,
    grantType: d.grantType,
  };
}

async function listTrackedGrantsFromApi(
  filter: ListTrackedGrantsFilter,
): Promise<TrackedGrantSummary[]> {
  const response = await fetchGrantLifecycleList({
    status: filter.status,
    all: filter.all,
    limit: 50,
  });
  return response.items.map(mapGrantTrackToSummary);
}

export async function listTrackedGrants(
  filter: ListTrackedGrantsFilter = {},
): Promise<TrackedGrantSummary[]> {
  if (!isMockDataSource()) {
    return listTrackedGrantsFromApi(filter);
  }

  await Promise.resolve();
  const { status, all } = filter;
  let rows = MOCK_TRACKED_GRANTS;
  if (status) {
    rows = rows.filter((g) => g.status === status);
  } else if (!all) {
    rows = rows.filter(
      (g) =>
        g.status !== "awarded" &&
        g.status !== "rejected" &&
        g.status !== "withdrawn" &&
        g.status !== "abandoned",
    );
  }
  return rows.map(toSummary);
}

export async function getTrackedGrantDetail(
  id: string,
): Promise<TrackedGrantDetail | null> {
  await Promise.resolve();
  return (
    MOCK_TRACKED_GRANTS.find((g) => g.id === id || g.grantId === id) ?? null
  );
}
