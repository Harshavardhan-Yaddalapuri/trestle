const COOKIE_NAME = "trestle_anon_session";
const COOKIE_MAX_AGE_DAYS = 30;

function generateUUID(): string {
  return crypto.randomUUID();
}

export function getSessionId(): string {
  if (typeof document === "undefined") return generateUUID();

  const existing = document.cookie
    .split("; ")
    .find((c) => c.startsWith(`${COOKIE_NAME}=`));

  if (existing) {
    return existing.split("=")[1];
  }

  const id = generateUUID();
  const maxAge = COOKIE_MAX_AGE_DAYS * 24 * 60 * 60;
  document.cookie = `${COOKIE_NAME}=${id}; path=/; max-age=${maxAge}; SameSite=Lax`;
  return id;
}
