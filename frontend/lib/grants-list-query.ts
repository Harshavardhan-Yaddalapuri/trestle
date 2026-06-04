import type { GrantLifecycleStatus } from "@/lib/domain/lifecycle";
import { isGrantLifecycleStatus } from "@/lib/domain/lifecycle";

export const GRANT_SORT_COLUMNS = ["name", "amount", "deadline", "status"] as const;
export type GrantSortColumn = (typeof GRANT_SORT_COLUMNS)[number];
export type GrantSortDirection = "asc" | "desc";

export interface GrantsListQuery {
  status?: GrantLifecycleStatus;
  all?: boolean;
  sort?: GrantSortColumn;
  dir?: GrantSortDirection;
}

export function isGrantSortColumn(value: string | undefined): value is GrantSortColumn {
  return value !== undefined && (GRANT_SORT_COLUMNS as readonly string[]).includes(value);
}

export function isGrantSortDirection(
  value: string | undefined,
): value is GrantSortDirection {
  return value === "asc" || value === "desc";
}

export function parseGrantsListQuery(searchParams: {
  status?: string;
  all?: string;
  sort?: string;
  dir?: string;
}): GrantsListQuery {
  const status = isGrantLifecycleStatus(searchParams.status)
    ? searchParams.status
    : undefined;
  const all = searchParams.all === "1" || searchParams.all === "true";
  const sort = isGrantSortColumn(searchParams.sort) ? searchParams.sort : undefined;
  const dir = isGrantSortDirection(searchParams.dir) ? searchParams.dir : undefined;
  return { status, all, sort, dir };
}

/** Build `/grants` URL preserving filters; toggles sort direction when clicking the active column. */
export function buildGrantsListHref(
  query: GrantsListQuery,
  column?: GrantSortColumn,
): string {
  const params = new URLSearchParams();

  if (query.status) {
    params.set("status", query.status);
  } else if (query.all) {
    params.set("all", "1");
  }

  if (column) {
    const nextDir: GrantSortDirection =
      query.sort === column && query.dir === "asc" ? "desc" : "asc";
    params.set("sort", column);
    params.set("dir", nextDir);
  } else if (query.sort) {
    params.set("sort", query.sort);
    if (query.dir) {
      params.set("dir", query.dir);
    }
  }

  const qs = params.toString();
  return qs ? `/grants?${qs}` : "/grants";
}
