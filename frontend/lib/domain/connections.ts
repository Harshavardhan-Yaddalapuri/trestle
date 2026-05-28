export type ConnectionType = "investor" | "mentor" | "operator" | "partner";

export type ConnectionStrength = "warm" | "intro_needed" | "cold";

export interface ConnectionSummary {
  id: string;
  name: string;
  title: string;
  company: string;
  type: ConnectionType;
  strength: ConnectionStrength;
  locationLabel: string;
  lastTouchedIso: string;
}

export interface ConnectionDetail extends ConnectionSummary {
  notes: string;
  suggestedNextAction: string;
  tags: string[];
}

