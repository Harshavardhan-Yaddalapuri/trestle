import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

import {
  ANON_SESSION_COOKIE,
  ANON_SESSION_MAX_AGE_SECONDS,
} from "@/lib/session-constants";

const ANON_SESSION_COOKIE_OPTIONS = {
  path: "/",
  maxAge: ANON_SESSION_MAX_AGE_SECONDS,
  sameSite: "lax" as const,
  httpOnly: false,
};

/** Ensure request cookies carry a stable anon id for downstream Server Components. */
function bootstrapAnonSession(request: NextRequest): void {
  if (!request.cookies.get(ANON_SESSION_COOKIE)?.value) {
    request.cookies.set(ANON_SESSION_COOKIE, crypto.randomUUID());
  }
}

/** Mirror anon session onto the response (required when Supabase rebuilds the response). */
function attachAnonSessionCookie(request: NextRequest, response: NextResponse): void {
  const id = request.cookies.get(ANON_SESSION_COOKIE)?.value;
  if (id) {
    response.cookies.set(ANON_SESSION_COOKIE, id, ANON_SESSION_COOKIE_OPTIONS);
  }
}

export async function middleware(request: NextRequest) {
  bootstrapAnonSession(request);
  let response = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            request.cookies.set(name, value)
          );
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
          attachAnonSessionCookie(request, response);
        },
      },
    }
  );

  // Refresh session if expired — important!
  await supabase.auth.getSession();

  attachAnonSessionCookie(request, response);
  return response;
}

export const config = {
  matcher: [
    // Skip Next.js internals and static files
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
