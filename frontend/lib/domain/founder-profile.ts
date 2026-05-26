export interface FounderProfile {
  schemaVersion: 1;
  companyName: string;
  companyWebsite: string | null;
  /** e.g. pre_seed, seed */
  fundingStage: string | null;
  headquarters: string | null;
  industries: string[];
  productSummary: string | null;
  targetMarket: string | null;
  /** Free-text or structured later */
  tractionSummary: string | null;
  arrOrRevenueBand: string | null;
  runwayBand: string | null;
  fundingGoal: string | null;
  /** Preferred program types */
  grantTypes: string[];
  geographicPreferences: string[];
  /** Forward-compatible bag */
  extras?: Record<string, unknown>;
}
