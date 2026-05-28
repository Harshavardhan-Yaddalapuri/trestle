import Link from "next/link";
import { listResources } from "@/lib/data/resources";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { ResourceCategory, ResourceStage } from "@/lib/domain/resources";

export const metadata = {
  title: "Resources — Trestle",
};

const CATEGORY_LABEL: Record<ResourceCategory, string> = {
  grant: "Grant",
  accelerator: "Accelerator",
  pitch_competition: "Pitch competition",
  coworking: "Coworking",
  event: "Event",
  mentor: "Mentor",
  tool: "Tool",
};

const STAGE_LABEL: Record<ResourceStage, string> = {
  idea: "Idea",
  pre_seed: "Pre-seed",
  seed: "Seed",
  series_a: "Series A",
  growth: "Growth",
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function fitTone(fit: "High match" | "Good match" | "Explore") {
  if (fit === "High match") return "border-primary/40 bg-primary-fixed text-on-primary-fixed";
  if (fit === "Good match") return "border-secondary bg-secondary-container text-on-secondary-container";
  return "border-outline bg-surface-container text-on-surface";
}

export default async function ResourcesPage() {
  const resources = await listResources();

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-8">
      <div>
        <h1
          className="font-[family-name:var(--font-plus-jakarta)] text-primary font-bold"
          style={{ fontSize: "28px", lineHeight: "36px" }}
        >
          Resources
        </h1>
        <p className="text-on-surface-variant mt-1 text-sm md:text-base max-w-2xl">
          A mock catalog of grants, accelerators, and programs discovered via Agentic Search.
        </p>
      </div>

      <section className="grid gap-6 lg:grid-cols-2">
        <Card className="border-outline-variant shadow-none bg-surface-container-lowest lg:col-span-2">
          <CardHeader>
            <CardTitle className="font-[family-name:var(--font-plus-jakarta)]">Suggested resources</CardTitle>
            <CardDescription>Mock results until the API is wired up.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            {resources.map((r) => (
              <article key={r.id} className="rounded-xl border border-outline-variant bg-card p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-medium text-on-surface line-clamp-2">{r.name}</p>
                    <p className="text-xs text-on-surface-variant mt-1">
                      {CATEGORY_LABEL[r.category]} · {r.locationLabel}
                    </p>
                  </div>
                  <Badge variant="outline" className={cn("rounded-full font-medium shrink-0", fitTone(r.fitBadge))}>
                    {r.fitBadge}
                  </Badge>
                </div>

                <div className="mt-3 flex flex-wrap gap-2 text-xs text-on-surface-variant">
                  <span className="rounded-full border border-outline-variant px-2 py-1">
                    Verified {formatDate(r.lastVerifiedIso)}
                  </span>
                  <span className="rounded-full border border-outline-variant px-2 py-1">
                    Stage: {r.stage.map((s) => STAGE_LABEL[s]).join(", ")}
                  </span>
                </div>

                <div className="mt-4 flex items-center justify-between">
                  <Link href="#" className="text-primary text-sm font-medium hover:underline">
                    View details
                  </Link>
                  <button
                    type="button"
                    className="text-on-surface-variant text-sm hover:text-primary transition-colors"
                    aria-label="Save resource"
                  >
                    <span className="material-symbols-outlined">bookmark</span>
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

