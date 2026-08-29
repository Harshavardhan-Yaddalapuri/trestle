import Link from "next/link";
import { fetchMatchedEvents } from "@/lib/api/events";
import type { ApiEventSummary } from "@/lib/api/events-types";
import type { ProfileOut } from "@/lib/api";
import { getProfileReadiness } from "@/lib/profile-readiness";
import { serverRequest } from "@/lib/api/server";

export const metadata = {
  title: "Events - Trestle",
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

export default async function EventsPage() {
  let events: ApiEventSummary[] = [];
  let loadError: string | null = null;
  let profile: ProfileOut | null = null;

  try {
    profile = await serverRequest<ProfileOut>("/api/users/profile");
    if (getProfileReadiness(profile).eventsReady) {
      const response = await fetchMatchedEvents({ limit: 50, minScore: 0.2 });
      events = response.results.map((row) => row.event);
    }
  } catch (err) {
    loadError =
      err instanceof Error ? err.message : "Could not load events from the API.";
  }

  const readiness = profile ? getProfileReadiness(profile) : null;

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
          Events matched to your saved founder profile.
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

      {readiness && !readiness.eventsReady ? (
        <div className="rounded-2xl bg-secondary-container/40 p-6 text-on-surface">
          <h2 className="font-medium">Complete your event preferences</h2>
          <p className="mt-1 text-sm text-on-surface-variant">
            Add your stage, industry, location, and goals so Trestle can rank events for you.
          </p>
          <Link className="mt-4 inline-flex rounded-full bg-primary px-4 py-2 text-sm font-medium text-on-primary" href="/profile">
            Complete profile
          </Link>
        </div>
      ) : (
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
                  No current events match your profile. Check back soon as sources update.
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
      )}
    </div>
  );
}
