import Link from "next/link";
import { fetchMatchedEvents } from "@/lib/api/events";
import type { ApiEventMatchResult } from "@/lib/api/events-types";
import type { ProfileOut } from "@/lib/api";
import { getProfileReadiness } from "@/lib/profile-readiness";
import { serverRequest } from "@/lib/api/server";
import { EventMatchesTable } from "./_components/EventMatchesTable";

export const metadata = {
  title: "Events - Trestle",
};

export default async function EventsPage() {
  let matches: ApiEventMatchResult[] = [];
  let loadError: string | null = null;
  let profile: ProfileOut | null = null;

  try {
    profile = await serverRequest<ProfileOut>("/api/users/profile");
    if (getProfileReadiness(profile).eventsReady) {
      const response = await fetchMatchedEvents({ limit: 50, minScore: 0.2 });
      matches = response.results;
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
        <EventMatchesTable
          matches={matches}
          profileState={profile?.incorporation_state ?? null}
          profileCountry={profile?.incorporation_country ?? null}
        />
      )}
    </div>
  );
}
