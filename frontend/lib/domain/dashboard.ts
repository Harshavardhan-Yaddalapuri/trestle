import type { GrantLifecycleStatus } from "./lifecycle";

export interface ActiveGrantCard {
  trackedGrantId: string;
  name: string;
  status: GrantLifecycleStatus;
  deadlineLabel: string | null;
  daysUntilDeadline: number | null;
  amountLabel: string | null;
}

export interface UpcomingDeadline {
  id: string;
  trackedGrantId: string;
  grantName: string;
  label: string;
  /** ISO */
  dueAt: string;
}

export interface RecentMatch {
  id: string;
  title: string;
  summary: string;
  /** ISO */
  matchedAt: string;
  confidenceLabel: string;
}

export interface DashboardHome {
  schemaVersion: 1;
  activeGrants: ActiveGrantCard[];
  upcomingDeadlines: UpcomingDeadline[];
  recentMatches: RecentMatch[];
}
