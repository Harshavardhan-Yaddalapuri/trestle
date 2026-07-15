import Link from "next/link";
import FilterDropdown from "@/components/filter-dropdown";
import { fetchEvents, fetchMatchedEvents } from "@/lib/api/events";
import type { ApiEventSummary } from "@/lib/api/events-types";
import {
  buildEventsListHref,
  EVENT_DEMO_PROFILE_LABELS,
  EVENT_DEMO_PROFILE_OPTIONS,
  parseEventsListQuery,
} from "@/lib/events-list-query";

export const metadata = {
  title: "Events - Trestle",
};

type PageProps = {
  searchParams: Promise<{
    profile?: string;
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

const DEMO_PROFILE_MATCH_PARAMS = {
  ai_seed_founder: {
    stage: "seed",
    industry: ["ai"],
    location: "new york",
    goals: ["fundraising", "networking"],
  },
  biotech_founder: {
    stage: "pre_seed",
    industry: ["biotech"],
    location: "cambridge",
    goals: ["partnerships", "lab access"],
  },
  climate_operator: {
    stage: "series_a",
    industry: ["climate"],
    location: "san francisco",
    goals: ["partnerships", "fundraising"],
  },
} as const;

export default async function EventsPage({ searchParams }: PageProps) {
  const sp = await searchParams;
  const query = parseEventsListQuery(sp);
  const selectedProfile = query.profile ?? "none";

  let events: ApiEventSummary[] = [];
  let loadError: string | null = null;

  try {
    if (selectedProfile === "none") {
      const response = await fetchEvents({ limit: 50 });
      events = response.items;
    } else {
      const response = await fetchMatchedEvents({
        ...DEMO_PROFILE_MATCH_PARAMS[selectedProfile],
        limit: 50,
        minScore: 0.2,
      });
      events = response.results.map((row) => row.event);
    }
  } catch (err) {
    loadError =
      err instanceof Error ? err.message : "Could not load events from the API.";
  }

  const profileOptions = EVENT_DEMO_PROFILE_OPTIONS.map((profile) => ({
    value: profile,
    label: EVENT_DEMO_PROFILE_LABELS[profile],
    href: buildEventsListHref({
      profile,
    }),
  }));

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
          Demo-friendly events from the local database. No login required.
        </p>
        {selectedProfile !== "none" ? (
          <p className="text-on-surface-variant mt-1 text-xs md:text-sm">
            Showing scored matches for: {EVENT_DEMO_PROFILE_LABELS[selectedProfile]}.
          </p>
        ) : null}
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
          label="Founder profile"
          options={profileOptions}
          value={selectedProfile}
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
                  No events found for this founder profile yet. Try switching to
                  "None (all events)".
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
                  <td className="px-4 py-3 text-on-surface-variant">
                    {event.is_virtual ? "Virtual" : "In person"}
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
