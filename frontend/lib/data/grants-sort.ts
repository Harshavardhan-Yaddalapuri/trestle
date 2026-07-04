import type { GrantSortColumn, GrantSortDirection } from "@/lib/grants-list-query";
import { LIFECYCLE_PIPELINE_ORDER } from "@/lib/domain/lifecycle";
import type { TrackedGrantSummary } from "@/lib/domain/tracked-grant";

function compareStrings(a: string, b: string): number {
  return a.localeCompare(b, undefined, { sensitivity: "base" });
}

function deadlineSortKey(iso: string | null): number {
  if (!iso) return Number.POSITIVE_INFINITY;
  const t = new Date(iso).getTime();
  return Number.isNaN(t) ? Number.POSITIVE_INFINITY : t;
}

function statusSortKey(status: TrackedGrantSummary["status"]): number {
  const idx = LIFECYCLE_PIPELINE_ORDER.indexOf(status);
  return idx === -1 ? LIFECYCLE_PIPELINE_ORDER.length : idx;
}

export function sortTrackedGrants(
  rows: TrackedGrantSummary[],
  sort: GrantSortColumn,
  dir: GrantSortDirection,
): TrackedGrantSummary[] {
  const mult = dir === "asc" ? 1 : -1;

  return [...rows].sort((a, b) => {
    let cmp = 0;

    switch (sort) {
      case "name":
        cmp = compareStrings(a.name, b.name);
        break;
      case "amount": {
        const aNull = a.amountMin == null;
        const bNull = b.amountMin == null;
        if (aNull && bNull) cmp = 0;
        else if (aNull) cmp = 1;
        else if (bNull) cmp = -1;
        else cmp = a.amountMin! - b.amountMin!;
        break;
      }
      case "deadline":
        cmp = deadlineSortKey(a.deadlineIso) - deadlineSortKey(b.deadlineIso);
        break;
      case "status":
        cmp = statusSortKey(a.status) - statusSortKey(b.status);
        break;
      default:
        cmp = 0;
    }

    if (cmp !== 0) return cmp * mult;
    return compareStrings(a.name, b.name);
  });
}
