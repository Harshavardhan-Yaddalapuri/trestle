"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { SearchInput } from "@/app/_components/SearchInput";
import { Loader2, ArrowLeft, ExternalLink } from "lucide-react";

export const dynamic = "force-dynamic";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type ResourceResult = {
  resource: {
    id: string;
    name: string;
    type: string;
    description: string | null;
    url: string | null;
    application_url: string | null;
    location: string[] | null;
    industry: string[] | null;
    stage: string[] | null;
    deadline: string | null;
    prize_amount: string | null;
    funding_range: string | null;
    eligibility: Record<string, unknown> | null;
    status: string;
    updated_at: string | null;
  };
  fit_explanation: string;
  next_step: string;
  confidence_badge: string;
  fit_score: number;
};

type SearchResponse = {
  query_parsed: {
    location: string | null;
    state: string | null;
    stage: string | null;
    need_type: string | null;
    timeline: string | null;
    industry: string[] | null;
    demographics: string[] | null;
    funding_range: string | null;
  };
  results: ResourceResult[];
  total_found: number;
};

function SearchResults() {
  const params = useSearchParams();
  const query = params.get("q") || "";

  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!query) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);

    fetch(`${API}/api/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, limit: 10 }),
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
        return res.json();
      })
      .then((json) => {
        if (!cancelled) setData(json);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [query]);

  return (
    <>
      {/* Intent chips */}
      {data?.query_parsed && (
        <div className="mb-6 flex flex-wrap gap-2">
          {Object.entries(data.query_parsed)
            .filter(([, v]) => v != null && (Array.isArray(v) ? v.length > 0 : true))
            .map(([k, v]) => (
              <span
                key={k}
                className="rounded-full bg-secondary-container px-3 py-1 text-xs font-medium text-on-secondary-container"
              >
                {k}: {Array.isArray(v) ? v.join(", ") : String(v)}
              </span>
            ))}
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}

      {error && (
        <div className="rounded-[1.5rem] bg-error-container p-6 text-sm text-on-error-container">
          Something went wrong: {error}
          <br />
          <span className="text-xs opacity-80">
            Make sure the backend is running at {API}
          </span>
        </div>
      )}

      {data && data.results.length === 0 && !loading && (
        <div className="rounded-[1.5rem] bg-surface-container p-8 text-center text-sm text-on-surface-variant">
          No matching resources found. Try broadening your search.
        </div>
      )}

      <div className="flex flex-col gap-4">
        {data?.results.map((r) => (
          <div
            key={r.resource.id}
            className="flex flex-col gap-3 rounded-[1.5rem] bg-surface-container p-6 transition hover:shadow-[0_1px_3px_rgba(0,0,0,0.05)]"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-primary-container px-3 py-0.5 text-xs font-medium text-on-primary-container">
                    {r.resource.type.replace("_", " ")}
                  </span>
                  <span className="text-xs text-on-surface-variant">
                    {r.confidence_badge}
                  </span>
                </div>
                <h3 className="font-[family-name:var(--font-plus-jakarta)] text-lg font-medium text-on-surface">
                  {r.resource.name}
                </h3>
              </div>
              <span className="shrink-0 text-xs font-semibold text-primary">
                {(r.fit_score * 100).toFixed(0)}% match
              </span>
            </div>

            <p className="text-sm leading-relaxed text-on-surface-variant">
              {r.resource.description || "No description available."}
            </p>

            <div className="flex flex-wrap gap-2">
              {r.resource.location?.map((loc) => (
                <span
                  key={loc}
                  className="rounded-full bg-surface-high px-2 py-0.5 text-xs text-on-surface-variant"
                >
                  📍 {loc}
                </span>
              ))}
              {r.resource.stage?.map((s) => (
                <span
                  key={s}
                  className="rounded-full bg-surface-high px-2 py-0.5 text-xs text-on-surface-variant"
                >
                  🚀 {s}
                </span>
              ))}
              {r.resource.deadline && (
                <span className="rounded-full bg-surface-high px-2 py-0.5 text-xs text-error">
                  ⏰ {r.resource.deadline}
                </span>
              )}
              {r.resource.funding_range && (
                <span className="rounded-full bg-surface-high px-2 py-0.5 text-xs text-on-surface-variant">
                  💰 {r.resource.funding_range}
                </span>
              )}
            </div>

            <div className="flex flex-col gap-1 rounded-[1rem] bg-surface-high p-4">
              <p className="text-sm text-on-surface">
                <span className="font-medium">Why it fits:</span>{" "}
                {r.fit_explanation}
              </p>
              <p className="text-sm text-primary">
                <span className="font-medium">Next step:</span>{" "}
                {r.next_step}
              </p>
            </div>

            <div className="flex gap-3">
              {r.resource.url && (
                <a
                  href={r.resource.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 rounded-full bg-primary px-4 py-2 text-xs font-medium text-on-primary transition hover:bg-primary-container hover:text-primary"
                >
                  Learn more <ExternalLink className="h-3 w-3" />
                </a>
              )}
              {r.resource.application_url && (
                <a
                  href={r.resource.application_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 rounded-full bg-secondary-container px-4 py-2 text-xs font-medium text-on-secondary-container transition hover:bg-secondary"
                >
                  Apply now <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

export default function SearchPage() {
  const params = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
  const query = params?.get("q") || "";

  return (
    <div className="min-h-screen bg-surface">
      {/* Nav */}
      <header className="border-b border-outline-variant bg-surface/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between px-6 py-4 md:px-8">
          <Link href="/" className="text-xl font-semibold tracking-tight text-primary">
            TRESTLE
          </Link>
          <Link
            href="/"
            className="flex items-center gap-1 text-sm text-on-surface-variant hover:text-on-surface"
          >
            <ArrowLeft className="h-4 w-4" /> Back
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-[1440px] px-6 py-10 md:px-8">
        <div className="mb-8 flex flex-col gap-4">
          <SearchInput defaultValue={query} />
          {query && (
            <p className="text-sm text-on-surface-variant">
              Results for <span className="font-medium text-on-surface">"{query}"</span>
            </p>
          )}
        </div>

        <Suspense fallback={
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        }>
          <SearchResults />
        </Suspense>
      </main>
    </div>
  );
}
