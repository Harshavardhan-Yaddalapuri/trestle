import Link from "next/link";
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
import { cn } from "@/lib/utils";

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

      <div className="flex flex-wrap gap-2">
        <FilterChip
          href={buildGrantsListHref({ sort: query.sort, dir: query.dir, all: true })}
          active={showAll && !status}
        >
          All
        </FilterChip>
        <FilterChip
          href={buildGrantsListHref({ sort: query.sort, dir: query.dir })}
          active={!showAll && !status}
        >
          In progress
        </FilterChip>
        {GRANT_LIFECYCLE_STATUSES.map((s) => (
          <FilterChip
            key={s}
            href={buildGrantsListHref({ sort: query.sort, dir: query.dir, status: s })}
            active={status === s}
          >
            {GRANT_LIFECYCLE_LABELS[s]}
          </FilterChip>
        ))}
      </div>

      <GrantsTable grants={grants} query={query} usingApi={usingApi} />
    </div>
  );
}

function FilterChip({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "rounded-full px-4 py-2 text-sm font-medium border transition-colors",
        active
          ? "bg-secondary-container text-on-secondary-container border-transparent"
          : "border-outline-variant text-on-surface-variant hover:bg-surface-variant/60",
      )}
    >
      {children}
    </Link>
  );
}
