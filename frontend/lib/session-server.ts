import { cookies } from "next/headers";

export const ANON_SESSION_COOKIE = "trestle_anon_session";

const MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

/**
 * Stable anonymous session for server-side API calls.
 * Mirrors backend `SessionMiddleware` cookie name and max-age.
 */
export async function getOrCreateServerSessionId(): Promise<string> {
  const store = await cookies();
  const existing = store.get(ANON_SESSION_COOKIE)?.value;
  if (existing) {
    return existing;
  }

  const id = crypto.randomUUID();
  store.set(ANON_SESSION_COOKIE, id, {
    path: "/",
    maxAge: MAX_AGE_SECONDS,
    sameSite: "lax",
    httpOnly: false,
  });
  return id;
}

/** Cookie header for outbound API requests from Server Components. */
export async function buildApiCookieHeader(): Promise<string> {
  const store = await cookies();
  const pairs = store.getAll().map((c) => `${c.name}=${c.value}`);
  if (!pairs.some((p) => p.startsWith(`${ANON_SESSION_COOKIE}=`))) {
    const id = await getOrCreateServerSessionId();
    pairs.push(`${ANON_SESSION_COOKIE}=${id}`);
  }
  return pairs.join("; ");
}
