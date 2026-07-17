import { listTrackedGrants } from "@/lib/data/tracked-grants";
import { sortTrackedGrants } from "@/lib/data/grants-sort";
import { isMockDataSource } from "@/lib/config/data-source";
import {
  GRANT_LIFECYCLE_STATUSES,
  GRANT_LIFECYCLE_LABELS,
} from "@/lib/domain/lifecycle";
import {
  buildGrantsListHref,
  parseGrantsListQuery,
} from "@/lib/grants-list-query";
import GrantsTable from "./_components/GrantsTable";
import FilterDropdown from "@/components/filter-dropdown";

export const metadata = {
  title: "Grants — Trestle",
};

type PageProps = {
  searchParams: Promise<{
    status?: string;
    all?: string;
    sort?: string;
    dir?: string;
  }>;
};

export default async function GrantsPage({ searchParams }: PageProps) {
  const sp = await searchParams;
  const query = parseGrantsListQuery(sp);
  const { status } = query;
  const showAll = query.all ?? false;

  let grants: Awaited<ReturnType<typeof listTrackedGrants>> = [];
  let loadError: string | null = null;

  try {
    grants = await listTrackedGrants({
      status,
      all: showAll && !status,
    });
    if (query.sort && query.dir) {
      grants = sortTrackedGrants(grants, query.sort, query.dir);
    }
  } catch (err) {
    loadError =
      err instanceof Error ? err.message : "Could not load grants from the API.";
  }

  const usingApi = !isMockDataSource();
  const statusOptions = [
    {
      value: "in_progress",
      label: "In progress",
      href: buildGrantsListHref({ sort: query.sort, dir: query.dir }),
    },
    {
      value: "all",
      label: "All",
      href: buildGrantsListHref({ sort: query.sort, dir: query.dir, all: true }),
    },
    ...GRANT_LIFECYCLE_STATUSES.map((s) => ({
      value: s,
      label: GRANT_LIFECYCLE_LABELS[s],
      href: buildGrantsListHref({ sort: query.sort, dir: query.dir, status: s }),
    })),
  ];
  const selectedStatus = status ?? (showAll ? "all" : "in_progress");

  return (
    <div className="p-4 md:p-8 max-w-5xl mx-auto space-y-6">
      <div>
        <h1
          className="font-[family-name:var(--font-plus-jakarta)] text-primary font-bold"
          style={{ fontSize: "28px", lineHeight: "36px" }}
        >
          Grants
        </h1>
        <p className="text-on-surface-variant mt-1 text-sm md:text-base">
          {usingApi
            ? "Tracked grants from your workspace, filtered by lifecycle status."
            : "Mock data — set NEXT_PUBLIC_DATA_SOURCE=api to use the backend."}
        </p>
      </div>

      {loadError ? (
        <div
          className="rounded-lg border border-error/30 bg-error-container/30 px-4 py-3 text-sm text-on-error-container"
          role="alert"
        >
          {loadError}
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <FilterDropdown
          label="Status"
          options={statusOptions}
          value={selectedStatus}
        />
      </div>

      <GrantsTable grants={grants} query={query} usingApi={usingApi} />
    </div>
  );
}
