import type { ConnectionDetail } from "@/lib/domain/connections";

const iso = (d: Date) => d.toISOString();

export const MOCK_CONNECTIONS: ConnectionDetail[] = [
  {
    id: "conn-001",
    name: "Anita Meyer",
    title: "CEO",
    company: "PayPulse",
    type: "operator",
    strength: "warm",
    locationLabel: "Detroit, MI",
    lastTouchedIso: iso(new Date("2026-05-18")),
    notes: "Met at FintechWeek. Interested in AI-driven compliance workflows.",
    suggestedNextAction: "Send a short update and ask for 2 intros to local angels.",
    tags: ["fintech", "warm intro"],
  },
  {
    id: "conn-002",
    name: "James Sterling",
    title: "Angel Investor",
    company: "Sterling Ventures",
    type: "investor",
    strength: "intro_needed",
    locationLabel: "London, UK",
    lastTouchedIso: iso(new Date("2026-05-05")),
    notes: "Likes pre-seed infra and B2B AI. Waiting on a crisp one-pager.",
    suggestedNextAction: "Ask your mentor for an intro; attach 1-page memo + metrics.",
    tags: ["infra", "pre-seed"],
  },
  {
    id: "conn-003",
    name: "Sofia Park",
    title: "Mentor",
    company: "Nimbus Accelerator",
    type: "mentor",
    strength: "cold",
    locationLabel: "Remote",
    lastTouchedIso: iso(new Date("2026-04-22")),
    notes: "Recommended by a founder on Twitter. No response yet.",
    suggestedNextAction: "Follow up once with a specific question and calendar link.",
    tags: ["go-to-market", "accelerators"],
  },
];

