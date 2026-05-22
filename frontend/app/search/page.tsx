"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { SearchInput } from "@/app/_components/SearchInput";
import { ArrowLeft } from "lucide-react";

function SearchContent() {
  const searchParams = useSearchParams();
  const stateParam = searchParams.get("state") || undefined;

  return (
    <>
      <SearchInput state={stateParam} />
      <Suspense fallback={<div className="py-20 text-center text-sm text-on-surface-variant">Searching...</div>}>
        <SearchResults state={stateParam} />
      </Suspense>
    </>
  );
}

function SearchResults({ state }: { state?: string }) {
  // Placeholder — real implementation calls /api/search with state param
  return <div className="text-center text-on-surface-variant">Loading results...</div>;
}

export default function SearchPage() {
  return (
    <div className="min-h-screen bg-surface">
      <header className="border-b border-outline-variant/40 px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <Link href="/" className="text-xl font-bold text-primary">TRESTLE</Link>
          <Link href="/" className="flex items-center gap-1 text-sm text-on-surface-variant">
            <ArrowLeft className="h-4 w-4" /> Back
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-6 py-10">
        <Suspense fallback={<div className="py-20 text-center text-sm text-on-surface-variant">Loading...</div>}>
          <SearchContent />
        </Suspense>
      </main>
    </div>
  );
}
