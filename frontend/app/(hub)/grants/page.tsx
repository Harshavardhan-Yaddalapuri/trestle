import Link from "next/link";
import { listTrackedGrants } from "@/lib/data/tracked-grants";
import {
  GRANT_LIFECYCLE_STATUSES,
  GRANT_LIFECYCLE_LABELS,
  isGrantLifecycleStatus,
} from "@/lib/domain/lifecycle";
import { LifecycleBadge } from "@/components/lifecycle-badge";
import { cn } from "@/lib/utils";

export const metadata = {
  title: "My Grants — Trestle",
};

type PageProps = {
  searchParams: Promise<{ status?: string }>;
};

export default async function GrantsPage({ searchParams }: PageProps) {
  const sp = await searchParams;
  const status = isGrantLifecycleStatus(sp.status) ? sp.status : undefined;
  const grants = await listTrackedGrants({ status });

  return (
    <div className="p-4 md:p-8 max-w-5xl mx-auto space-y-6">
      <div>
        <h1
          className="font-[family-name:var(--font-plus-jakarta)] text-primary font-bold"
          style={{ fontSize: "28px", lineHeight: "36px" }}
        >
          My Grants
        </h1>
        <p className="text-on-surface-variant mt-1 text-sm md:text-base">
          Filter by lifecycle status. Data loads from the mock adapter until the API is ready.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <FilterChip href="/grants" active={!status}>
          All
        </FilterChip>
        {GRANT_LIFECYCLE_STATUSES.map((s) => (
          <FilterChip key={s} href={`/grants?status=${s}`} active={status === s}>
            {GRANT_LIFECYCLE_LABELS[s]}
          </FilterChip>
        ))}
      </div>

      <div className="rounded-xl border border-outline-variant overflow-hidden bg-surface-container-lowest">
        <table className="w-full text-left text-sm">
          <thead className="bg-surface-container text-on-surface-variant text-xs uppercase tracking-wide">
            <tr>
              <th className="px-4 py-3 font-medium">Grant</th>
              <th className="px-4 py-3 font-medium hidden sm:table-cell">Amount</th>
              <th className="px-4 py-3 font-medium hidden md:table-cell">Deadline</th>
              <th className="px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {grants.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-on-surface-variant">
                  No grants in this status.
                </td>
              </tr>
            ) : (
              grants.map((g) => (
                <tr key={g.id} className="border-t border-outline-variant hover:bg-surface-variant/40">
                  <td className="px-4 py-3">
                    <Link href={`/grants/${g.id}`} className="font-medium text-primary hover:underline">
                      {g.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-on-surface-variant hidden sm:table-cell">
                    {g.amountLabel ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-on-surface-variant hidden md:table-cell">
                    {g.deadlineLabel ?? "—"}
                  </td>
                  <td className="px-4 py-3">
                    <LifecycleBadge status={g.status} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FilterChip({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "rounded-full px-4 py-2 text-sm font-medium border transition-colors",
        active
          ? "bg-secondary-container text-on-secondary-container border-transparent"
          : "border-outline-variant text-on-surface-variant hover:bg-surface-variant/60",
      )}
    >
      {children}
    </Link>
  );
}
