"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

export function SearchInput({ defaultValue = "" }: { defaultValue?: string }) {
  const [q, setQ] = useState(defaultValue);
  const router = useRouter();

  const submit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!q.trim()) return;
    router.push(`/search?q=${encodeURIComponent(q.trim())}`);
  };

  return (
    <form onSubmit={submit} className="flex w-full max-w-lg items-center gap-2">
      <div className="relative flex-1">
        <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface-variant" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="What are you looking for?"
          className="w-full rounded-full bg-surface-container py-3 pl-10 pr-4 text-sm outline-none ring-1 ring-outline-variant transition placeholder:text-on-surface-variant/50 focus:ring-2 focus:ring-primary"
        />
      </div>
      <button
        type="submit"
        className="rounded-full bg-primary px-5 py-3 text-sm font-medium text-on-primary transition hover:bg-primary-container hover:text-primary"
      >
        Search
      </button>
    </form>
  );
}
