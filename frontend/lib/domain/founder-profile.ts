/**
 * Legacy mock-data shape retained for isolated fixture modules only.
 *
 * Product profile screens use `ProfileIn` and `ProfileOut` from `@/lib/api`;
 * do not use this type for persisted founder data.
 */
export interface FounderProfile {
  schemaVersion: 1;
  companyName: string;
  companyWebsite: string | null;
  fundingStage: string | null;
  headquarters: string | null;
  industries: string[];
  productSummary: string | null;
  targetMarket: string | null;
  tractionSummary: string | null;
  arrOrRevenueBand: string | null;
  runwayBand: string | null;
  fundingGoal: string | null;
  grantTypes: string[];
  geographicPreferences: string[];
  extras?: Record<string, unknown>;
}
