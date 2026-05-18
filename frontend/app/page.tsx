"use client";

import { useState } from "react";
import Link from "next/link";
import { Search, ArrowRight, ShieldCheck, RefreshCw, MessageSquare } from "lucide-react";

export default function LandingPage() {
  const [query, setQuery] = useState("");

  return (
    <div className="min-h-screen bg-surface">
      {/* Nav */}
      <header className="border-b border-outline-variant/40">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="text-xl font-bold tracking-tight text-primary">TRESTLE</span>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm font-medium text-on-surface-variant hover:text-on-surface">
              Sign In
            </Link>
            <Link
              href="/signup"
              className="rounded-full bg-primary px-5 py-2 text-sm font-semibold text-on-primary"
            >
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <main className="mx-auto max-w-3xl px-6 py-20 text-center">
        <h1 className="mb-6 text-4xl font-bold leading-tight text-on-surface md:text-5xl">
          Find resources that are
          <br />
          <span className="text-primary">still true</span>.
        </h1>
        <p className="mx-auto mb-10 max-w-lg text-lg text-on-surface-variant">
          Trestle is an AI agent for startup founders. Ask anything — it scrapes live, verifies freshness,
          and tells you what is actually still open.
        </p>

        {/* Search Input */}
        <div className="mx-auto flex max-w-xl items-center gap-2 rounded-full bg-surface-container px-4 py-3 ring-1 ring-outline-variant/50">
          <Search className="h-5 w-5 text-on-surface-variant" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && query.trim()) {
                window.location.href = `/search?q=${encodeURIComponent(query)}`;
              }
            }}
            placeholder="What grants are open for pre-revenue founders in Detroit?"
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-on-surface-variant/50"
          />
          <button
            onClick={() => query.trim() && (window.location.href = `/search?q=${encodeURIComponent(query)}`)}
            className="flex h-9 w-9 items-center justify-center rounded-full bg-primary text-on-primary"
          >
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>

        {/* Features */}
        <div className="mt-16 grid gap-6 md:grid-cols-3">
          <div className="rounded-2xl bg-surface-container p-6 text-left">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
              <RefreshCw className="h-5 w-5 text-primary" />
            </div>
            <h3 className="mb-2 font-semibold text-on-surface">Live Scraping</h3>
            <p className="text-sm text-on-surface-variant">
              We scrape resource pages in real time. No stale directories.
            </p>
          </div>

          <div className="rounded-2xl bg-surface-container p-6 text-left">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
              <ShieldCheck className="h-5 w-5 text-primary" />
            </div>
            <h3 className="mb-2 font-semibold text-on-surface">Freshness Verified</h3>
            <p className="text-sm text-on-surface-variant">
              Every result shows when it was last checked. Dead links flagged automatically.
            </p>
          </div>

          <div className="rounded-2xl bg-surface-container p-6 text-left">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
              <MessageSquare className="h-5 w-5 text-primary" />
            </div>
            <h3 className="mb-2 font-semibold text-on-surface">Personalized</h3>
            <p className="text-sm text-on-surface-variant">
              The agent remembers your stage, industry, and goals. Answers improve over time.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
