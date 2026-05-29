"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { supabase } from "@/lib/supabase";

export default function Nav() {
  const [session, setSession] = useState<boolean | null>(null); // null = loading

  useEffect(() => {
    // Check initial session
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(!!s);
    });

    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(!!s);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const isLoggedIn = session === true;

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

        {/* Auth-aware CTAs: loading state prevents flash of wrong buttons */}
        {session === null ? (
          <div className="flex items-center gap-3">
            <div className="h-8 w-20 animate-pulse rounded bg-surface-variant/30" />
            <div className="h-9 w-32 animate-pulse rounded-full bg-surface-variant/30" />
          </div>
        ) : isLoggedIn ? (
          <div className="flex items-center gap-3">
            <Button asChild className="rounded-full font-bold">
              <Link href="/dashboard">Dashboard</Link>
            </Button>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm font-medium text-on-surface-variant hover:text-primary transition-colors duration-200"
            >
              Log In
            </Link>
            <Button asChild className="rounded-full font-bold">
              <Link href="/signup">Start Building</Link>
            </Button>
          </div>
        )}
      </div>
    </nav>
  );
}
