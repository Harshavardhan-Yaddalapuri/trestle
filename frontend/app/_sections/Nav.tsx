"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { supabase } from "@/lib/supabase";

export default function Nav() {
  const [session, setSession] = useState<unknown>(undefined);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event: string, s) => {
      setSession(s);
    });

    return () => subscription.unsubscribe();
  }, []);

  return (
    <nav className="fixed top-0 z-50 w-full bg-surface/80 backdrop-blur-md">
      <div className="flex justify-between items-center w-full px-4 md:px-8 py-4 max-w-[1440px] mx-auto">
        <div className="flex items-center gap-8">
          <Link
            href="/"
            className="font-[family-name:var(--font-plus-jakarta)] tracking-tight font-bold text-primary"
            style={{ fontSize: "28px", lineHeight: "36px" }}
          >
            TRESTLE
          </Link>

          <div className="hidden md:flex gap-6 items-center">
            <Link href="/" className="text-primary border-b-2 border-primary font-bold pb-1 transition-colors duration-200">
              Platform
            </Link>
            <Link href="/search" className="text-on-surface-variant font-medium hover:text-primary transition-colors duration-200">
              Agents
            </Link>
            <Link href="#pricing" className="text-on-surface-variant font-medium hover:text-primary transition-colors duration-200">
              Pricing
            </Link>
            <Link href="#community" className="text-on-surface-variant font-medium hover:text-primary transition-colors duration-200">
              Community
            </Link>
          </div>
        </div>

        {/* Auth-aware right side */}
        <div className="flex items-center gap-4">
          {session === undefined ? (
            // Loading state — shimmer placeholders
            <>
              <div className="h-8 w-20 rounded-full bg-surface-variant animate-pulse hidden md:block" />
              <div className="h-10 w-36 rounded-full bg-surface-variant animate-pulse" />
            </>
          ) : session ? (
            // Logged in
            <Button asChild className="rounded-full font-bold">
              <Link href="/dashboard">Dashboard</Link>
            </Button>
          ) : (
            // Logged out
            <>
              <Link
                href="/login"
                className="text-on-surface-variant font-medium hover:text-primary transition-colors duration-200 hidden md:inline"
              >
                Log In
              </Link>
              <Button asChild className="rounded-full font-bold">
                <Link href="/signup">Start Building</Link>
              </Button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
