import Link from "next/link";
import type { GrantSortColumn, GrantSortDirection, GrantsListQuery } from "@/lib/grants-list-query";
import { buildGrantsListHref } from "@/lib/grants-list-query";
import type { TrackedGrantSummary } from "@/lib/domain/tracked-grant";
import { LifecycleBadge } from "@/components/lifecycle-badge";
import { cn } from "@/lib/utils";

type GrantsTableProps = {
  grants: TrackedGrantSummary[];
  query: GrantsListQuery;
  usingApi: boolean;
};

export default function GrantsTable({ grants, query, usingApi }: GrantsTableProps) {
  return (
    <div className="rounded-xl border border-outline-variant overflow-hidden bg-surface-container-lowest">
      <table className="w-full text-left text-sm">
        <thead className="bg-surface-container text-on-surface-variant text-xs uppercase tracking-wide">
          <tr>
            <SortableHeader column="name" label="Grant" query={query} className="px-4 py-3" />
            <SortableHeader
              column="amount"
              label="Amount"
              query={query}
              className="px-4 py-3 hidden sm:table-cell"
            />
            <SortableHeader
              column="deadline"
              label="Deadline"
              query={query}
              className="px-4 py-3 hidden md:table-cell"
            />
            <SortableHeader column="status" label="Status" query={query} className="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          {grants.length === 0 ? (
            <tr>
              <td colSpan={4} className="px-4 py-8 text-center text-on-surface-variant">
                {usingApi
                  ? "No tracked grants yet. Save a grant from search or chat to see it here."
                  : "No grants in this status."}
              </td>
            </tr>
          ) : (
            grants.map((g) => (
              <tr
                key={g.trackId}
                className="border-t border-outline-variant hover:bg-surface-variant/40"
              >
                <td className="px-4 py-3">
                  <Link
                    href={`/grants/${encodeURIComponent(g.id)}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {g.name}
                  </Link>
                  {g.providerName ? (
                    <p className="text-xs text-on-surface-variant mt-0.5">{g.providerName}</p>
                  ) : null}
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
  );
}

function SortableHeader({
  column,
  label,
  query,
  className,
}: {
  column: GrantSortColumn;
  label: string;
  query: GrantsListQuery;
  className?: string;
}) {
  const active = query.sort === column;
  const dir: GrantSortDirection = active && query.dir ? query.dir : "asc";
  const href = buildGrantsListHref(query, column);

  return (
    <th className={className} aria-sort={active ? (dir === "asc" ? "ascending" : "descending") : "none"}>
      <Link
        href={href}
        className={cn(
          "inline-flex items-center gap-1 font-medium hover:text-on-surface transition-colors",
          active && "text-on-surface",
        )}
      >
        {label}
        <SortIndicator active={active} dir={dir} />
      </Link>
    </th>
  );
}

function SortIndicator({
  active,
  dir,
}: {
  active: boolean;
  dir: GrantSortDirection;
}) {
  return (
    <span className="inline-flex flex-col text-[10px] leading-none opacity-70" aria-hidden>
      <span className={cn(active && dir === "asc" ? "text-primary" : "text-on-surface-variant/40")}>
        ▲
      </span>
      <span
        className={cn(
          "-mt-0.5",
          active && dir === "desc" ? "text-primary" : "text-on-surface-variant/40",
        )}
      >
        ▼
      </span>
    </span>
  );
}
