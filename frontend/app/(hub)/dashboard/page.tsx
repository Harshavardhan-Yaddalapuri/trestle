import Link from "next/link";
import { loadDashboardHome } from "@/lib/data/dashboard";
import { LifecycleBadge } from "@/components/lifecycle-badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export const metadata = {
  title: "Dashboard — Trestle",
};

function formatDue(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default async function DashboardPage() {
  const data = await loadDashboardHome();

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-8">
      <div>
        <h1
          className="font-[family-name:var(--font-plus-jakarta)] text-primary font-bold"
          style={{ fontSize: "28px", lineHeight: "36px" }}
        >
          Dashboard
        </h1>
        <p className="text-on-surface-variant mt-1 text-sm md:text-base max-w-2xl">
          Tracked grants, upcoming deadlines, and recent discovery matches (mock data).
        </p>
      </div>

      <section className="grid gap-6 lg:grid-cols-2">
        <Card className="border-outline-variant shadow-none lg:col-span-2 bg-surface-container-lowest">
          <CardHeader>
            <CardTitle className="font-[family-name:var(--font-plus-jakarta)]">
              Active grants
            </CardTitle>
            <CardDescription>Saved, applied, or in review — needs your attention soon.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            {data.activeGrants.length === 0 ? (
              <p className="text-on-surface-variant text-sm">No active grants yet.</p>
            ) : (
              data.activeGrants.map((g) => (
                <Link
                  key={g.trackedGrantId}
                  href={`/grants/${g.trackedGrantId}`}
                  className="rounded-xl border border-outline-variant p-4 hover:border-primary transition-colors bg-card"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-medium text-on-surface line-clamp-2">{g.name}</p>
                    <LifecycleBadge status={g.status} className="shrink-0" />
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs text-on-surface-variant">
                    {g.amountLabel && <span>{g.amountLabel}</span>}
                    {g.deadlineLabel && (
                      <span>
                        Due {g.deadlineLabel}
                        {g.daysUntilDeadline !== null ? ` · ${g.daysUntilDeadline}d` : ""}
                      </span>
                    )}
                  </div>
                </Link>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="border-outline-variant shadow-none bg-surface-container-lowest">
          <CardHeader>
            <CardTitle className="font-[family-name:var(--font-plus-jakarta)]">
              Upcoming deadlines
            </CardTitle>
            <CardDescription>Ordered soonest first.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.upcomingDeadlines.map((d) => (
              <Link
                key={d.id}
                href={`/grants/${d.trackedGrantId}`}
                className="flex items-center justify-between gap-3 rounded-lg border border-transparent px-2 py-2 hover:bg-surface-variant/60"
              >
                <div>
                  <p className="text-sm font-medium text-on-surface line-clamp-1">{d.grantName}</p>
                  <p className="text-xs text-on-surface-variant">{d.label}</p>
                </div>
                <time className="text-xs font-medium text-primary whitespace-nowrap" dateTime={d.dueAt}>
                  {formatDue(d.dueAt)}
                </time>
              </Link>
            ))}
          </CardContent>
        </Card>

        <Card className="border-outline-variant shadow-none bg-surface-container-lowest">
          <CardHeader>
            <CardTitle className="font-[family-name:var(--font-plus-jakarta)]">
              Recent matches
            </CardTitle>
            <CardDescription>From Agent Hub discovery (illustrative).</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {data.recentMatches.map((m) => (
              <article key={m.id} className="border-b border-outline-variant last:border-0 pb-4 last:pb-0">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-sm font-semibold text-on-surface">{m.title}</h3>
                  <span className="text-[11px] uppercase tracking-wide text-primary font-medium shrink-0">
                    {m.confidenceLabel}
                  </span>
                </div>
                <p className="text-sm text-on-surface-variant mt-1">{m.summary}</p>
                <time className="text-xs text-on-surface-variant mt-2 block" dateTime={m.matchedAt}>
                  {formatDue(m.matchedAt)}
                </time>
              </article>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
