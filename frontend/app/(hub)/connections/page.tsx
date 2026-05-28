import Link from "next/link";
import { listConnections } from "@/lib/data/connections";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { ConnectionStrength, ConnectionType } from "@/lib/domain/connections";

export const metadata = {
  title: "Connections — Trestle",
};

const TYPE_LABEL: Record<ConnectionType, string> = {
  investor: "Investor",
  mentor: "Mentor",
  operator: "Operator",
  partner: "Partner",
};

const STRENGTH_LABEL: Record<ConnectionStrength, string> = {
  warm: "Warm",
  intro_needed: "Intro needed",
  cold: "Cold",
};

function strengthTone(strength: ConnectionStrength) {
  if (strength === "warm") return "border-primary/40 bg-primary-fixed text-on-primary-fixed";
  if (strength === "intro_needed") return "border-secondary bg-secondary-container text-on-secondary-container";
  return "border-outline bg-surface-container text-on-surface";
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default async function ConnectionsPage() {
  const connections = await listConnections();

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-8">
      <div>
        <h1
          className="font-[family-name:var(--font-plus-jakarta)] text-primary font-bold"
          style={{ fontSize: "28px", lineHeight: "36px" }}
        >
          Connections
        </h1>
        <p className="text-on-surface-variant mt-1 text-sm md:text-base max-w-2xl">
          Mock relationship tracking for mentors, investors, and operators. Replace with real CRM data later.
        </p>
      </div>

      <section className="grid gap-6 lg:grid-cols-2">
        <Card className="border-outline-variant shadow-none bg-surface-container-lowest lg:col-span-2">
          <CardHeader>
            <CardTitle className="font-[family-name:var(--font-plus-jakarta)]">Your network</CardTitle>
            <CardDescription>Quickly see who to follow up with next.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            {connections.map((c) => (
              <article key={c.id} className="rounded-xl border border-outline-variant bg-card p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-medium text-on-surface line-clamp-1">{c.name}</p>
                    <p className="text-xs text-on-surface-variant mt-1 line-clamp-1">
                      {c.title} · {c.company}
                    </p>
                  </div>
                  <Badge
                    variant="outline"
                    className={cn("rounded-full font-medium shrink-0", strengthTone(c.strength))}
                  >
                    {STRENGTH_LABEL[c.strength]}
                  </Badge>
                </div>

                <div className="mt-3 flex flex-wrap gap-2 text-xs text-on-surface-variant">
                  <span className="rounded-full border border-outline-variant px-2 py-1">
                    {TYPE_LABEL[c.type]}
                  </span>
                  <span className="rounded-full border border-outline-variant px-2 py-1">{c.locationLabel}</span>
                  <span className="rounded-full border border-outline-variant px-2 py-1">
                    Last touched {formatDate(c.lastTouchedIso)}
                  </span>
                </div>

                <div className="mt-4 flex items-center justify-between">
                  <Link href="#" className="text-primary text-sm font-medium hover:underline">
                    Open
                  </Link>
                  <button
                    type="button"
                    className="text-on-surface-variant text-sm hover:text-primary transition-colors"
                    aria-label="Log activity"
                  >
                    <span className="material-symbols-outlined">edit_note</span>
                  </button>
                </div>
              </article>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

