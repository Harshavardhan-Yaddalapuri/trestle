import "server-only";

import type {
  ApiGrantDetail,
  ApiGrantLifecycleEventListResponse,
  ApiGrantLifecycleListResponse,
  ApiGrantTrackOut,
  GrantLifecycleStatus,
} from "@/lib/api/grants-types";
import { GRANT_LIFECYCLE_STATUSES } from "@/lib/domain/lifecycle";
import { serverRequest } from "@/lib/api/server";

export interface ListGrantLifecycleParams {
  /** Single lifecycle status, or omit with `all` for every status. */
  status?: GrantLifecycleStatus;
  /** When true, include terminal statuses (awarded, rejected, …). */
  all?: boolean;
  limit?: number;
  cursor?: string;
}

export async function fetchGrantLifecycleList(
  params: ListGrantLifecycleParams = {},
): Promise<ApiGrantLifecycleListResponse> {
  const query: Record<string, string> = {};

  if (params.all) {
    query.status = GRANT_LIFECYCLE_STATUSES.join(",");
  } else if (params.status) {
    query.status = params.status;
  }

  if (params.limit !== undefined) {
    query.limit = String(params.limit);
  }
  if (params.cursor) {
    query.cursor = params.cursor;
  }

  return serverRequest<ApiGrantLifecycleListResponse>("/api/grants/lifecycle", {
    params: Object.keys(query).length > 0 ? query : undefined,
  });
}

export async function fetchGrantDetail(grantRef: string): Promise<ApiGrantDetail> {
  return serverRequest<ApiGrantDetail>(
    `/api/grants/${encodeURIComponent(grantRef)}`,
  );
}

export async function fetchGrantLifecycleEvents(
  grantRef: string,
): Promise<ApiGrantLifecycleEventListResponse> {
  return serverRequest<ApiGrantLifecycleEventListResponse>(
    `/api/grants/${encodeURIComponent(grantRef)}/lifecycle/events`,
  );
}

function matchesGrantRef(item: ApiGrantTrackOut, grantRef: string): boolean {
  return (
    item.grant.source_id === grantRef ||
    item.grant.id === grantRef ||
    item.id === grantRef
  );
}

/** Scan paginated lifecycle rows for a track matching source id, grant id, or track id. */
export async function findGrantTrackByRef(
  grantRef: string,
): Promise<ApiGrantTrackOut | null> {
  let cursor: string | undefined;

  do {
    const response = await fetchGrantLifecycleList({
      all: true,
      limit: 50,
      cursor,
    });

    const match = response.items.find((item) => matchesGrantRef(item, grantRef));
    if (match) return match;

    cursor = response.next_cursor ?? undefined;
  } while (cursor);

  return null;
}
