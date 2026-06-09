import type {
  ApiGrantDetail,
  ApiGrantLifecycleEventOut,
  ApiGrantTrackOut,
} from "@/lib/api/grants-types";
import {
  GRANT_LIFECYCLE_LABELS,
  type GrantLifecycleStatus,
} from "@/lib/domain/lifecycle";
import type {
  GrantNote,
  GrantTimelineEvent,
  TrackedGrantDetail,
  TrackedGrantSummary,
} from "@/lib/domain/tracked-grant";

function formatDeadline(deadline: string | null, rolling: boolean): {
  label: string | null;
  iso: string | null;
} {
  if (rolling && !deadline) {
    return { label: "Rolling", iso: null };
  }
  if (!deadline) {
    return { label: null, iso: null };
  }
  const d = new Date(`${deadline}T12:00:00`);
  if (Number.isNaN(d.getTime())) {
    return { label: deadline, iso: deadline };
  }
  return {
    label: d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    }),
    iso: deadline,
  };
}

export function mapGrantTrackToSummary(item: ApiGrantTrackOut): TrackedGrantSummary {
  const { grant } = item;
  const { label, iso } = formatDeadline(grant.deadline, grant.rolling);

  return {
    trackId: item.id,
    id: grant.source_id,
    grantId: grant.id,
    catalogResourceId: grant.source_id,
    name: grant.name,
    status: item.lifecycle_status as GrantLifecycleStatus,
    amountLabel: grant.amount_display ?? null,
    amountMin: grant.amount_min,
    deadlineLabel: label,
    deadlineIso: iso,
    updatedAt: item.lifecycle_updated_at,
    providerName: grant.provider_name,
    grantType: grant.type,
  };
}

function formatEligibility(eligibility: Record<string, unknown>): string | null {
  const entries = Object.entries(eligibility);
  if (entries.length === 0) return null;
  return entries
    .map(([key, value]) => {
      const rendered = Array.isArray(value) ? value.join(", ") : String(value);
      return `${key}: ${rendered}`;
    })
    .join("; ");
}

export function mapLifecycleEventsToTimeline(
  events: ApiGrantLifecycleEventOut[],
): GrantTimelineEvent[] {
  return events.map((event) => ({
    id: event.id,
    at: event.created_at,
    kind: event.from_status === null ? "created" : "status_change",
    title:
      event.from_status === null
        ? "Added to pipeline"
        : `Status: ${GRANT_LIFECYCLE_LABELS[event.to_status]}`,
    detail: event.note ?? undefined,
  }));
}

function mapTrackNote(track: ApiGrantTrackOut): GrantNote[] {
  if (!track.note) return [];
  return [
    {
      id: `track-note-${track.id}`,
      body: track.note,
      authorLabel: "You",
      createdAt: track.created_at,
    },
  ];
}

export function mapGrantTrackToDetail(
  track: ApiGrantTrackOut,
  grantDetail: ApiGrantDetail | null,
  events: ApiGrantLifecycleEventOut[],
): TrackedGrantDetail {
  const summary = mapGrantTrackToSummary(track);
  const metadata = track.lifecycle_metadata ?? {};
  const extensions =
    Object.keys(metadata).length > 0 ? metadata : undefined;

  return {
    ...summary,
    description: grantDetail?.description ?? null,
    eligibilitySummary: grantDetail
      ? formatEligibility(grantDetail.eligibility)
      : null,
    sourceUrl: grantDetail?.url ?? null,
    applicationUrl: grantDetail?.application_url ?? null,
    timeline: mapLifecycleEventsToTimeline(events),
    nextSteps: [],
    notes: mapTrackNote(track),
    extensions,
  };
}
