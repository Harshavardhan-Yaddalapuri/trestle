import Link from "next/link";
import FilterDropdown from "@/components/filter-dropdown";
import { fetchEvents } from "@/lib/api/events";
import type { ApiEventSummary } from "@/lib/api/events-types";
import {
  buildEventsListHref,
  EVENT_INDUSTRY_LABELS,
  EVENT_INDUSTRY_OPTIONS,
  EVENT_STAGE_LABELS,
  EVENT_STAGE_OPTIONS,
  parseEventsListQuery,
} from "@/lib/events-list-query";

export const metadata = {
  title: "Events - Trestle",
};

type PageProps = {
  searchParams: Promise<{
    stage?: string;
    industry?: string;
    include_expired?: string;
  }>;
};

function formatDateRange(startsAt: string, endsAt: string | null): string {
  const start = new Date(startsAt);
  const startLabel = start.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  if (!endsAt) return startLabel;
  const end = new Date(endsAt);
  const endLabel = end.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  return `${startLabel} - ${endLabel}`;
}

function getLocationLabel(event: ApiEventSummary): string {
  return event.location_text ?? event.city ?? event.region ?? event.country ?? "Virtual";
}

export default async function EventsPage({ searchParams }: PageProps) {
  const sp = await searchParams;
  const query = parseEventsListQuery(sp);

  let events: ApiEventSummary[] = [];
  let loadError: string | null = null;

  try {
    const response = await fetchEvents({
      stage: query.stage,
      industry: query.industry,
      includeExpired: query.includeExpired,
      limit: 50,
    });
    events = response.items;
  } catch (err) {
    loadError =
      err instanceof Error ? err.message : "Could not load events from the API.";
  }

  const stageOptions = [
    {
      value: "all",
      label: "All stages",
      href: buildEventsListHref({
        industry: query.industry,
        includeExpired: query.includeExpired,
      }),
    },
    ...EVENT_STAGE_OPTIONS.map((stage) => ({
      value: stage,
      label: EVENT_STAGE_LABELS[stage],
      href: buildEventsListHref({
        stage,
        industry: query.industry,
        includeExpired: query.includeExpired,
      }),
    })),
  ];

  const industryOptions = [
    {
      value: "all",
      label: "All industries",
      href: buildEventsListHref({
        stage: query.stage,
        includeExpired: query.includeExpired,
      }),
    },
    ...EVENT_INDUSTRY_OPTIONS.map((industry) => ({
      value: industry,
      label: EVENT_INDUSTRY_LABELS[industry],
      href: buildEventsListHref({
        stage: query.stage,
        industry,
        includeExpired: query.includeExpired,
      }),
    })),
  ];

  const recencyOptions = [
    {
      value: "upcoming",
      label: "Upcoming only",
      href: buildEventsListHref({
        stage: query.stage,
        industry: query.industry,
        includeExpired: false,
      }),
    },
    {
      value: "all_time",
      label: "Include expired",
      href: buildEventsListHref({
        stage: query.stage,
        industry: query.industry,
        includeExpired: true,
      }),
    },
  ];

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-6">
      <div>
        <h1
          className="font-[family-name:var(--font-plus-jakarta)] text-primary font-bold"
          style={{ fontSize: "28px", lineHeight: "36px" }}
        >
          Events
        </h1>
        <p className="text-on-surface-variant mt-1 text-sm md:text-base">
          Founder events discovered by the backend and filtered by your interests.
        </p>
      </div>

      {loadError ? (
        <div
          className="rounded-lg border border-error/30 bg-error-container/30 px-4 py-3 text-sm text-on-error-container"
          role="alert"
        >
          {loadError}
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <FilterDropdown
          label="Stage"
          options={stageOptions}
          value={query.stage ?? "all"}
        />
        <FilterDropdown
          label="Industry"
          options={industryOptions}
          value={query.industry ?? "all"}
        />
        <FilterDropdown
          label="Window"
          options={recencyOptions}
          value={query.includeExpired ? "all_time" : "upcoming"}
        />
      </div>

      <div className="rounded-xl border border-outline-variant overflow-hidden bg-surface-container-lowest">
        <table className="w-full text-left text-sm">
          <thead className="bg-surface-container text-on-surface-variant text-xs uppercase tracking-wide">
            <tr>
              <th className="px-4 py-3">Event</th>
              <th className="px-4 py-3 hidden md:table-cell">Date</th>
              <th className="px-4 py-3 hidden lg:table-cell">Location</th>
              <th className="px-4 py-3">Format</th>
            </tr>
          </thead>
          <tbody>
            {events.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-on-surface-variant">
                  No events match these filters yet.
                </td>
              </tr>
            ) : (
              events.map((event) => (
                <tr
                  key={event.id}
                  className="border-t border-outline-variant hover:bg-surface-variant/40"
                >
                  <td className="px-4 py-3">
                    <Link
                      className="font-medium text-primary hover:underline"
                      href={event.url}
                      rel="noopener noreferrer"
                      target="_blank"
                    >
                      {event.name}
                    </Link>
                    <p className="mt-0.5 text-xs text-on-surface-variant line-clamp-2">
                      {event.description}
                    </p>
                  </td>
                  <td className="px-4 py-3 text-on-surface-variant hidden md:table-cell">
                    {formatDateRange(event.starts_at, event.ends_at)}
                  </td>
                  <td className="px-4 py-3 text-on-surface-variant hidden lg:table-cell">
                    {getLocationLabel(event)}
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded-full border border-outline-variant px-2 py-1 text-xs text-on-surface">
                      {event.is_virtual ? "Virtual" : "In person"}
                    </span>
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
