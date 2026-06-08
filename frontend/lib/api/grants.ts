import "server-only";

import type {
  ApiGrantLifecycleListResponse,
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
