import { cookies } from "next/headers";
import { cache } from "react";

import { ANON_SESSION_COOKIE } from "@/lib/session-constants";

export { ANON_SESSION_COOKIE } from "@/lib/session-constants";

/** Resolve a stable anonymous session id for the current server request. */
const getRequestScopedAnonSessionId = cache(async (): Promise<string> => {
  const store = await cookies();
  return store.get(ANON_SESSION_COOKIE)?.value ?? crypto.randomUUID();
});

/** Read anonymous session id from request cookies (bootstrapped in middleware). */
export async function getServerSessionId(): Promise<string | undefined> {
  const store = await cookies();
  return store.get(ANON_SESSION_COOKIE)?.value;
}

/** Cookie header for outbound API requests from Server Components. */
export async function buildApiCookieHeader(): Promise<string> {
  const store = await cookies();
  const pairs = store.getAll().map((c) => `${c.name}=${c.value}`);
  if (!pairs.some((p) => p.startsWith(`${ANON_SESSION_COOKIE}=`))) {
    // Cookies can only be persisted in route handlers/actions; use a request-stable
    // fallback id so multiple server-side API calls in one render remain consistent.
    const anonSessionId = await getRequestScopedAnonSessionId();
    pairs.push(`${ANON_SESSION_COOKIE}=${anonSessionId}`);
  }
  return pairs.join("; ");
}
