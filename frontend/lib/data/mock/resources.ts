import type { ResourceDetail } from "@/lib/domain/resources";

const iso = (d: Date) => d.toISOString();

export const MOCK_RESOURCES: ResourceDetail[] = [
  {
    id: "res-001",
    name: "Michigan AI Innovation Fund",
    category: "grant",
    locationLabel: "Michigan, USA",
    stage: ["pre_seed", "seed"],
    fitBadge: "High match",
    lastVerifiedIso: iso(new Date("2026-05-20")),
    description:
      "Non-dilutive funding to help early-stage AI startups in Michigan hire, build, and validate go-to-market.",
    sourceUrl: "https://michigan.gov/",
    nextStep: "Draft a 1-page technical approach and budget, then request office hours.",
    tags: ["non-dilutive", "AI/ML", "state program"],
  },
  {
    id: "res-002",
    name: "Nimbus Seed Accelerator",
    category: "accelerator",
    locationLabel: "Remote · US-friendly",
    stage: ["idea", "pre_seed"],
    fitBadge: "Good match",
    lastVerifiedIso: iso(new Date("2026-05-10")),
    description:
      "A 10-week program focused on founder-market fit, customer discovery, and investor readiness for technical teams.",
    sourceUrl: "https://example.com/nimbus",
    nextStep: "Prepare a 90-second demo video and a 10-slide deck before applying.",
    tags: ["mentorship", "demo day", "remote"],
  },
  {
    id: "res-003",
    name: "Great Lakes Pitch Week",
    category: "pitch_competition",
    locationLabel: "Chicago, IL",
    stage: ["seed", "series_a"],
    fitBadge: "Explore",
    lastVerifiedIso: iso(new Date("2026-04-28")),
    description:
      "Regional pitch competition with investor matchmaking and non-cash perks for finalists.",
    sourceUrl: "https://example.com/great-lakes-pitch",
    nextStep: "Confirm eligibility and nominate a 5-minute live pitch speaker.",
    tags: ["pitch", "networking", "midwest"],
  },
];

