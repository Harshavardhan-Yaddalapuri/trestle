import Link from "next/link";
import type { TrackedGrantDetail } from "@/lib/domain/tracked-grant";
import { LifecycleBadge } from "@/components/lifecycle-badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import GrantActionsBar from "./GrantActionsBar";

function formatWhen(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function GrantDetailView({ grant }: { grant: TrackedGrantDetail }) {
  const extEntries = grant.extensions ? Object.entries(grant.extensions) : [];

  return (
    <div className="p-4 md:p-8 max-w-4xl mx-auto space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Link href="/grants" className="text-sm text-primary font-medium hover:underline">
            ← Grants
          </Link>
          <h1
            className="font-[family-name:var(--font-plus-jakarta)] text-primary font-bold mt-2"
            style={{ fontSize: "26px", lineHeight: "34px" }}
          >
            {grant.name}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <LifecycleBadge status={grant.status} />
            {grant.amountLabel && (
              <span className="text-sm text-on-surface-variant">{grant.amountLabel}</span>
            )}
            {grant.deadlineLabel && (
              <span className="text-sm text-on-surface-variant">Deadline: {grant.deadlineLabel}</span>
            )}
          </div>
        </div>
        <div className="flex gap-2 shrink-0">
          {grant.sourceUrl && (
            <a
              href={grant.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-primary hover:underline"
            >
              Source
            </a>
          )}
        </div>
      </div>

      <Card className="border-outline-variant shadow-none bg-surface-container-lowest">
        <CardHeader>
          <CardTitle className="text-base">Actions</CardTitle>
          <CardDescription>Buttons preview UX; server actions arrive with the API.</CardDescription>
        </CardHeader>
        <CardContent>
          <GrantActionsBar grantName={grant.name} />
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="border-outline-variant shadow-none bg-surface-container-lowest lg:col-span-3">
          <CardHeader>
            <CardTitle className="font-[family-name:var(--font-plus-jakarta)]">Lifecycle timeline</CardTitle>
            <CardDescription>Event types can expand when the backend schema is fixed.</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-5 border-l-2 border-primary/40 pl-4 ml-1">
              {grant.timeline.map((ev) => (
                <li key={ev.id}>
                  <p className="text-sm font-semibold text-on-surface">{ev.title}</p>
                  {ev.detail && (
                    <p className="text-sm text-on-surface-variant mt-1">{ev.detail}</p>
                  )}
                  <time className="text-xs text-on-surface-variant mt-1 block" dateTime={ev.at}>
                    {formatWhen(ev.at)}
                  </time>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <div className="space-y-6 lg:col-span-2">
          <Card className="border-outline-variant shadow-none bg-surface-container-lowest">
            <CardHeader>
              <CardTitle className="font-[family-name:var(--font-plus-jakarta)]">Next steps</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {grant.nextSteps.length === 0 ? (
                <p className="text-sm text-on-surface-variant">No steps yet.</p>
              ) : (
                grant.nextSteps.map((s) => (
                  <div
                    key={s.id}
                    className="rounded-lg border border-outline-variant px-3 py-2 bg-card"
                  >
                    <p className={`text-sm font-medium ${s.done ? "line-through text-on-surface-variant" : "text-on-surface"}`}>
                      {s.title}
                    </p>
                    {s.description && (
                      <p className="text-xs text-on-surface-variant mt-1">{s.description}</p>
                    )}
                    {s.dueDate && (
                      <p className="text-xs text-primary mt-1">Due {formatWhen(s.dueDate)}</p>
                    )}
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="border-outline-variant shadow-none bg-surface-container-lowest">
            <CardHeader>
              <CardTitle className="font-[family-name:var(--font-plus-jakarta)]">Notes</CardTitle>
              <CardDescription>Read-only mock; collaborative notes need an API.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {grant.notes.length === 0 ? (
                <p className="text-sm text-on-surface-variant">No notes yet.</p>
              ) : (
                grant.notes.map((n) => (
                  <div key={n.id} className="rounded-lg bg-surface-container px-3 py-2">
                    <p className="text-sm text-on-surface whitespace-pre-wrap">{n.body}</p>
                    <p className="text-xs text-on-surface-variant mt-2">
                      {n.authorLabel} · {formatWhen(n.createdAt)}
                    </p>
                  </div>
                ))
              )}
              <Separator />
              <p className="text-xs text-on-surface-variant">
                Adding notes from the UI will connect once persistence is defined.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {(grant.description || grant.eligibilitySummary) && (
        <Card className="border-outline-variant shadow-none bg-surface-container-lowest">
          <CardHeader>
            <CardTitle className="font-[family-name:var(--font-plus-jakarta)]">Overview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-on-surface-variant">
            {grant.description && <p>{grant.description}</p>}
            {grant.eligibilitySummary && (
              <p>
                <span className="font-medium text-on-surface">Eligibility: </span>
                {grant.eligibilitySummary}
              </p>
            )}
            {grant.catalogResourceId && (
              <p className="text-xs">
                Catalog ID: <code className="bg-surface-variant px-1 rounded">{grant.catalogResourceId}</code>
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {extEntries.length > 0 && (
        <Card className="border-outline-variant shadow-none bg-surface-container-lowest">
          <CardHeader>
            <CardTitle className="font-[family-name:var(--font-plus-jakarta)]">Extension fields</CardTitle>
            <CardDescription>Unknown or forward-compatible keys from the adapter.</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
              {extEntries.map(([k, v]) => (
                <div key={k} className="rounded-lg border border-outline-variant px-3 py-2">
                  <dt className="text-xs font-medium text-on-surface-variant uppercase tracking-wide">{k}</dt>
                  <dd className="text-on-surface mt-1 break-all">{String(v)}</dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
