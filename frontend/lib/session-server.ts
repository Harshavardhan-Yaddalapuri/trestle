import { cookies } from "next/headers";

import { ANON_SESSION_COOKIE } from "@/lib/session-constants";

export { ANON_SESSION_COOKIE } from "@/lib/session-constants";

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
    // Middleware should have set trestle_anon_session; ephemeral fallback only.
    pairs.push(`${ANON_SESSION_COOKIE}=${crypto.randomUUID()}`);
  }
  return pairs.join("; ");
}
