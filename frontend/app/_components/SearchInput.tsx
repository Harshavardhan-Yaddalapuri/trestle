"use client";

import { useState } from "react";
import { Search, ArrowRight } from "lucide-react";

export function SearchInput({ defaultValue = "", state }: { defaultValue?: string; state?: string }) {
  const [query, setQuery] = useState(defaultValue);

  function buildUrl() {
    let url = `/search?q=${encodeURIComponent(query)}`;
    if (state) url += `&state=${encodeURIComponent(state)}`;
    return url;
  }

  return (
    <div className="flex items-center gap-2 rounded-full bg-surface-container px-4 py-3 ring-1 ring-outline-variant/50">
      <Search className="h-5 w-5 text-on-surface-variant" />
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && query.trim()) {
            window.location.href = buildUrl();
          }
        }}
        placeholder="Search resources..."
        className="flex-1 bg-transparent text-sm outline-none placeholder:text-on-surface-variant/50"
      />
      <button
        onClick={() => query.trim() && (window.location.href = buildUrl())}
        className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-on-primary"
      >
        <ArrowRight className="h-4 w-4" />
      </button>
    </div>
  );
}
