"use client";

/**
 * Dashboard page — requires authenticated session.
 * Redirects to /login if no active session is found.
 */
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import type { Session } from "@supabase/supabase-js";

export default function DashboardPage() {
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function checkSession() {
      const { data } = await supabase.auth.getSession();
      if (!data.session) {
        router.push("/login");
      } else {
        setSession(data.session);
      }
      setLoading(false);
    }
    checkSession();
  }, [router]);

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.push("/");
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <p className="text-sm text-on-surface-variant">Loading...</p>
      </div>
    );
  }

  if (!session) {
    return null;
  }

  return (
    <div className="min-h-screen bg-surface">
      <header className="border-b border-outline-variant/20 px-6 py-4">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <h1 className="text-xl font-bold tracking-tight text-on-surface">TRESTLE</h1>
          <button
            onClick={handleSignOut}
            className="rounded-full bg-surface-container px-4 py-2 text-sm font-medium text-on-surface-variant hover:bg-surface-container-highest transition-colors"
          >
            Sign Out
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-12">
        <div className="rounded-2xl border border-outline-variant/10 bg-surface-container p-8">
          <h2 className="text-lg font-semibold text-on-surface">Welcome to your dashboard</h2>
          <p className="mt-2 text-sm text-on-surface-variant">
            You are signed in as <span className="font-medium text-on-surface">{session.user.email}</span>.
          </p>
        </div>
      </main>
    </div>
  );
}
