import type { DashboardHome } from "@/lib/domain/dashboard";
import type { FounderProfile } from "@/lib/domain/founder-profile";
import type { UserSettings } from "@/lib/domain/settings";
import type { TrackedGrantDetail } from "@/lib/domain/tracked-grant";

const iso = (d: Date) => d.toISOString();

const nextMonth = new Date();
nextMonth.setMonth(nextMonth.getMonth() + 1);

const twoWeeks = new Date();
twoWeeks.setDate(twoWeeks.getDate() + 14);

export const MOCK_TRACKED_GRANTS: TrackedGrantDetail[] = [
  {
    id: "tracked-001",
    catalogResourceId: "res-mi-ai-fund",
    name: "Michigan AI Innovation Fund",
    status: "under_review",
    amountLabel: "$50k – $150k",
    deadlineLabel: "Aug 15, 2026",
    deadlineIso: "2026-08-15T23:59:59.000Z",
    updatedAt: iso(new Date("2026-05-20")),
    description:
      "Non-dilutive support for early-stage AI companies headquartered in Michigan.",
    eligibilitySummary: "Michigan HQ, pre-seed/seed, AI as core product.",
    sourceUrl: "https://michigan.gov/",
    applicationUrl: "https://example.com/apply/mi-ai",
    timeline: [
      {
        id: "ev-1",
        at: iso(new Date("2026-04-01")),
        kind: "created",
        title: "Added to pipeline",
        detail: "Saved from Agentic Search results.",
      },
      {
        id: "ev-2",
        at: iso(new Date("2026-04-18")),
        kind: "status_change",
        title: "Status: Applied",
        detail: "LOI submitted through portal.",
      },
      {
        id: "ev-3",
        at: iso(new Date("2026-05-01")),
        kind: "status_change",
        title: "Status: Under review",
        detail: "Program office acknowledged receipt.",
      },
      {
        id: "ev-4",
        at: "2026-08-15T23:59:59.000Z",
        kind: "deadline",
        title: "Application deadline",
      },
    ],
    nextSteps: [
      {
        id: "ns-1",
        title: "Upload audited financials",
        description: "Required before technical review panel.",
        dueDate: iso(twoWeeks),
        done: false,
      },
      {
        id: "ns-2",
        title: "Schedule office hours with mentor",
        done: true,
      },
    ],
    notes: [
      {
        id: "n-1",
        body: "Program officer suggested stronger GTM metrics slide.",
        authorLabel: "You",
        createdAt: iso(new Date("2026-05-10")),
      },
    ],
    extensions: { reviewPanelWeek: "2026-06-02" },
  },
  {
    id: "tracked-002",
    catalogResourceId: null,
    name: "SBIR Phase I — NSF",
    status: "applied",
    amountLabel: "Up to $275k",
    deadlineLabel: "Jun 30, 2026",
    deadlineIso: "2026-06-30T23:59:59.000Z",
    updatedAt: iso(new Date("2026-05-22")),
    description: "Federal R&D funding for transformative technologies.",
    eligibilitySummary: "US-based small business, R&D focus.",
    sourceUrl: "https://www.nsf.gov/",
    applicationUrl: null,
    timeline: [
      {
        id: "ev-sb-1",
        at: iso(new Date("2026-05-12")),
        kind: "created",
        title: "Added to pipeline",
      },
      {
        id: "ev-sb-2",
        at: iso(new Date("2026-05-22")),
        kind: "status_change",
        title: "Status: Applied",
        detail: "Project Pitch submitted.",
      },
    ],
    nextSteps: [
      {
        id: "ns-sb-1",
        title: "Confirm SAM.gov registration is active",
        dueDate: iso(new Date("2026-05-28")),
        done: false,
      },
    ],
    notes: [],
  },
  {
    id: "tracked-003",
    catalogResourceId: "res-local-accelerator",
    name: "Detroit Mobility Challenge Grant",
    status: "saved",
    amountLabel: "$25k",
    deadlineLabel: "Jul 1, 2026",
    deadlineIso: "2026-07-01T23:59:59.000Z",
    updatedAt: iso(new Date("2026-05-01")),
    description: "Pilot funding for mobility startups in Southeast Michigan.",
    eligibilitySummary: "Detroit metro, MVP with pilot LOI.",
    sourceUrl: "https://example.com/mobility",
    applicationUrl: "https://example.com/mobility/apply",
    timeline: [
      {
        id: "ev-m-1",
        at: iso(new Date("2026-05-01")),
        kind: "created",
        title: "Added to pipeline",
      },
    ],
    nextSteps: [
      {
        id: "ns-m-1",
        title: "Draft one-page pilot scope",
        done: false,
      },
    ],
    notes: [
      {
        id: "n-m-1",
        body: "Check if insurance cert is required at submission.",
        authorLabel: "You",
        createdAt: iso(new Date("2026-05-02")),
      },
    ],
  },
  {
    id: "tracked-004",
    catalogResourceId: null,
    name: "Regional Innovation Seed Fund",
    status: "awarded",
    amountLabel: "$40k",
    deadlineLabel: null,
    deadlineIso: null,
    updatedAt: iso(new Date("2026-03-15")),
    description: "Regional seed fund for hardware-adjacent startups.",
    eligibilitySummary: "Great Lakes region, TRL 4+.",
    sourceUrl: "https://example.com/seed",
    applicationUrl: null,
    timeline: [
      {
        id: "ev-r-1",
        at: iso(new Date("2025-11-01")),
        kind: "created",
        title: "Added to pipeline",
      },
      {
        id: "ev-r-2",
        at: iso(new Date("2026-02-01")),
        kind: "status_change",
        title: "Status: Awarded",
        detail: "Executed agreement; first tranche scheduled.",
      },
    ],
    nextSteps: [
      {
        id: "ns-r-1",
        title: "Submit first milestone report",
        dueDate: iso(nextMonth),
        done: false,
      },
    ],
    notes: [],
  },
  {
    id: "tracked-005",
    catalogResourceId: null,
    name: "CleanTech Fast Grant",
    status: "rejected",
    amountLabel: "$100k",
    deadlineLabel: "Mar 1, 2026",
    deadlineIso: "2026-03-01T23:59:59.000Z",
    updatedAt: iso(new Date("2026-03-05")),
    description: "Rapid grant for climate tech pilots.",
    eligibilitySummary: "Carbon reduction KPI required.",
    sourceUrl: "https://example.com/cleantech",
    applicationUrl: null,
    timeline: [
      {
        id: "ev-c-1",
        at: iso(new Date("2026-01-10")),
        kind: "created",
        title: "Added to pipeline",
      },
      {
        id: "ev-c-2",
        at: iso(new Date("2026-03-05")),
        kind: "status_change",
        title: "Status: Rejected",
        detail: "Eligibility: stage outside current window.",
      },
    ],
    nextSteps: [],
    notes: [
      {
        id: "n-c-1",
        body: "Re-apply in Q3 when revenue threshold met.",
        authorLabel: "You",
        createdAt: iso(new Date("2026-03-06")),
      },
    ],
  },
];

export const MOCK_DASHBOARD_HOME: DashboardHome = {
  schemaVersion: 1,
  activeGrants: MOCK_TRACKED_GRANTS.filter((g) =>
    ["saved", "applied", "under_review"].includes(g.status),
  ).map((g) => ({
    trackedGrantId: g.id,
    name: g.name,
    status: g.status,
    deadlineLabel: g.deadlineLabel,
    amountLabel: g.amountLabel,
    daysUntilDeadline: g.deadlineIso
      ? Math.max(
          0,
          Math.ceil(
            (new Date(g.deadlineIso).getTime() - Date.now()) /
              (1000 * 60 * 60 * 24),
          ),
        )
      : null,
  })),
  upcomingDeadlines: MOCK_TRACKED_GRANTS.filter((g) => g.deadlineIso)
    .sort(
      (a, b) =>
        new Date(a.deadlineIso!).getTime() - new Date(b.deadlineIso!).getTime(),
    )
    .slice(0, 4)
    .map((g) => ({
      id: `dl-${g.id}`,
      trackedGrantId: g.id,
      grantName: g.name,
      label: g.deadlineLabel || "Deadline",
      dueAt: g.deadlineIso!,
    })),
  recentMatches: [
    {
      id: "match-1",
      title: "Michigan AI Innovation Fund",
      summary:
        "Strong fit: Michigan HQ, AI core product, and stage within program range.",
      matchedAt: iso(new Date("2026-05-24")),
      confidenceLabel: "High match",
    },
    {
      id: "match-2",
      title: "Detroit Mobility Challenge Grant",
      summary: "Moderate fit: add pilot LOI to improve eligibility score.",
      matchedAt: iso(new Date("2026-05-21")),
      confidenceLabel: "Good match",
    },
    {
      id: "match-3",
      title: "University Tech Transfer Micro-grant",
      summary: "Exploratory: confirm IP assignment with counsel.",
      matchedAt: iso(new Date("2026-05-18")),
      confidenceLabel: "Worth reviewing",
    },
  ],
};

export const MOCK_FOUNDER_PROFILE: FounderProfile = {
  schemaVersion: 1,
  companyName: "Northline Analytics",
  companyWebsite: "https://northline.example",
  fundingStage: "seed",
  headquarters: "Ann Arbor, MI",
  industries: ["AI/ML", "GovTech"],
  productSummary:
    "Compliance automation copilot for state procurement workflows.",
  targetMarket: "US state & local agencies, mid-market GovTech vendors.",
  tractionSummary: "3 paid pilots, 2 LOIs in Michigan.",
  arrOrRevenueBand: "< $500k ARR",
  runwayBand: "10–12 months",
  fundingGoal: "$1.5M seed to expand sales and SOC2.",
  grantTypes: ["Non-dilutive R&D", "Pilot programs", "Accelerator stipends"],
  geographicPreferences: ["Michigan", "Great Lakes", "Federal"],
  extras: { teamSize: "8" },
};

export const MOCK_USER_SETTINGS: UserSettings = {
  schemaVersion: 1,
  notifications: {
    emailAlerts: true,
    inAppAlerts: true,
    weeklyDigest: false,
    alertFrequency: "daily",
  },
};
