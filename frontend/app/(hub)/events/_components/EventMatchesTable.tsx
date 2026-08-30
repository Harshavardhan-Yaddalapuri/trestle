"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api";
import type { ApiEventMatchResult } from "@/lib/api/events-types";

type LocationFilter = "anywhere" | "state" | "country";
type FormatFilter = "all" | "in_person" | "virtual";

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

function getLocationLabel(event: ApiEventMatchResult["event"]): string {
  return event.location_text ?? event.city ?? event.region ?? event.country ?? "Virtual";
}

export function EventMatchesTable({
  matches,
  profileState,
  profileCountry,
}: {
  matches: ApiEventMatchResult[];
  profileState: string | null;
  profileCountry: string | null;
}) {
  const [locationFilter, setLocationFilter] = useState<LocationFilter>("anywhere");
  const [format, setFormat] = useState<FormatFilter>("all");
  const [filteredMatches, setFilteredMatches] = useState(matches);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let isCurrent = true;
    setIsLoading(true);
    setLoadError(null);

    apiClient.matchEvents({
      locationScope: locationFilter,
      eventFormat: format,
    })
      .then((response) => {
        if (isCurrent) setFilteredMatches(response.results);
      })
      .catch(() => {
        if (isCurrent) setLoadError("Could not update event filters. Please try again.");
      })
      .finally(() => {
        if (isCurrent) setIsLoading(false);
      });

    return () => {
      isCurrent = false;
    };
  }, [format, locationFilter]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 rounded-xl bg-surface-container p-4 sm:flex-row sm:items-end">
        <label className="grid gap-1.5 text-sm font-medium text-on-surface">
          Location
          <select
            aria-label="Filter events by location"
            className="h-10 rounded-md border border-outline-variant bg-surface-container-lowest px-3 text-sm font-normal"
            value={locationFilter}
            onChange={(event) => setLocationFilter(event.target.value as LocationFilter)}
          >
            <option value="anywhere">Anywhere</option>
            <option value="state" disabled={profileCountry !== "US" || !profileState}>
              In my state
            </option>
            <option value="country" disabled={!profileCountry}>
              {profileCountry ? `In ${profileCountry}` : "In my country"}
            </option>
          </select>
        </label>
        <label className="grid gap-1.5 text-sm font-medium text-on-surface">
          Format
          <select
            aria-label="Filter events by format"
            className="h-10 rounded-md border border-outline-variant bg-surface-container-lowest px-3 text-sm font-normal"
            value={format}
            onChange={(event) => setFormat(event.target.value as FormatFilter)}
          >
            <option value="all">All formats</option>
            <option value="in_person">In person only</option>
            <option value="virtual">Virtual only</option>
          </select>
        </label>
      </div>

      {loadError ? <p role="alert" className="text-sm text-error">{loadError}</p> : null}
      <div className="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest">
        <table className="w-full text-left text-sm">
          <thead className="bg-surface-container text-xs uppercase tracking-wide text-on-surface-variant">
            <tr>
              <th className="px-4 py-3">Event</th>
              <th className="hidden w-40 whitespace-nowrap px-5 py-3 md:table-cell">Date</th>
              <th className="hidden px-4 py-3 lg:table-cell">Location</th>
              <th className="px-4 py-3">Format</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-on-surface-variant">
                  Updating matches…
                </td>
              </tr>
            ) : filteredMatches.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-on-surface-variant">
                  No events match these filters.
                </td>
              </tr>
            ) : (
              filteredMatches.map(({ event }) => (
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
                    <p className="mt-0.5 line-clamp-2 text-xs text-on-surface-variant">
                      {event.description}
                    </p>
                  </td>
                  <td className="hidden w-40 whitespace-nowrap px-5 py-3 text-on-surface-variant md:table-cell">
                    {formatDateRange(event.starts_at, event.ends_at)}
                  </td>
                  <td className="hidden px-4 py-3 text-on-surface-variant lg:table-cell">
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
