import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

import {
  ANON_SESSION_COOKIE,
  ANON_SESSION_MAX_AGE_SECONDS,
} from "@/lib/session-constants";

const BYPASS_AUTH =
  process.env.NEXT_PUBLIC_BYPASS_AUTH?.toLowerCase() === "true";

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
  let session: unknown = null;
  if (!BYPASS_AUTH) {
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() {
            return request.cookies.getAll();
          },
          setAll(cookiesToSet: { name: string; value: string; options?: object }[]) {
            cookiesToSet.forEach((cookie: { name: string; value: string; options?: object }) =>
              request.cookies.set(cookie.name, cookie.value)
            );
            response = NextResponse.next({ request });
            cookiesToSet.forEach((cookie: { name: string; value: string; options?: object }) =>
              response.cookies.set(cookie.name, cookie.value, cookie.options)
            );
            attachAnonSessionCookie(request, response);
          },
        },
      }
    );

    // Refresh session if expired — important!
    const {
      data: { session: activeSession },
    } = await supabase.auth.getSession();
    session = activeSession;
  }

  // Protected route enforcement: redirect unauthenticated users to /login
  // TODO(auth): remove bypass once Supabase auth is stable across envs.
  const protectedPrefixes = ["/dashboard", "/search", "/events", "/profile", "/grants", "/settings", "/connections", "/resources"];
  const isProtected = protectedPrefixes.some((p) =>
    request.nextUrl.pathname.startsWith(p)
  );
  if (!BYPASS_AUTH && isProtected && !session) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  // Redirect already-authenticated users away from login/signup
  const authPages = ["/login", "/signup"];
  const isAuthPage = authPages.includes(request.nextUrl.pathname);
  if (!BYPASS_AUTH && isAuthPage && session) {
    const dashboardUrl = new URL("/dashboard", request.url);
    return NextResponse.redirect(dashboardUrl);
  }

  attachAnonSessionCookie(request, response);
  return response;
}

export const config = {
  matcher: [
    // Skip Next.js internals and static files
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
