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
import type { MatchResult, ProfileOut } from "@/lib/api";
import { serverRequest } from "@/lib/api/server";
import { getProfileReadiness } from "@/lib/profile-readiness";

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
  let recommendations: MatchResult[] = [];
  let recommendationsReady = false;

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

  try {
    const profile = await serverRequest<ProfileOut>("/api/users/profile");
    recommendationsReady = getProfileReadiness(profile).grantsReady;
    if (recommendationsReady) {
      const response = await serverRequest<{ results: MatchResult[] }>("/api/grants/match", {
        method: "POST",
        body: { limit: 3, min_score: 0.2 },
      });
      recommendations = response.results;
    }
  } catch {
    recommendationsReady = false;
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

      <section className="rounded-2xl bg-secondary-container/40 p-5">
        <h2 className="font-[family-name:var(--font-plus-jakarta)] text-lg font-medium text-on-surface">
          Recommended for your company
        </h2>
        {recommendationsReady ? (
          recommendations.length ? (
            <ul className="mt-3 space-y-2">
              {recommendations.map((match) => (
                <li key={match.grant.id} className="text-sm text-on-surface">
                  <span className="font-medium">{match.grant.name}</span>
                  <span className="text-on-surface-variant"> · {match.explanation}</span>
                </li>
              ))}
            </ul>
          ) : <p className="mt-2 text-sm text-on-surface-variant">No current grant matches. New opportunities are checked as sources refresh.</p>
        ) : (
          <p className="mt-2 text-sm text-on-surface-variant">
            Add your stage, industry, location, and incorporation status to see grant recommendations. <a className="font-medium text-primary hover:underline" href="/profile">Complete profile</a>
          </p>
        )}
      </section>

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
