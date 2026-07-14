import "server-only";

import type { ApiEventListResponse } from "@/lib/api/events-types";
import { serverRequest } from "@/lib/api/server";

export interface ListEventsParams {
  limit?: number;
  industry?: string;
  stage?: string;
  location?: string;
  includeExpired?: boolean;
}

export async function fetchEvents(
  params: ListEventsParams = {},
): Promise<ApiEventListResponse> {
  const query: Record<string, string> = {};
  if (params.limit !== undefined) {
    query.limit = String(params.limit);
  }
  if (params.industry) {
    query.industry = params.industry;
  }
  if (params.stage) {
    query.stage = params.stage;
  }
  if (params.location) {
    query.location = params.location;
  }
  if (params.includeExpired) {
    query.include_expired = "1";
  }

  return serverRequest<ApiEventListResponse>("/api/events", {
    params: Object.keys(query).length > 0 ? query : undefined,
  });
}
