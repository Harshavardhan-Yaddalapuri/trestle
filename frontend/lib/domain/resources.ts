export type ResourceCategory =
  | "grant"
  | "accelerator"
  | "pitch_competition"
  | "coworking"
  | "event"
  | "mentor"
  | "tool";

export type ResourceStage = "idea" | "pre_seed" | "seed" | "series_a" | "growth";

export interface ResourceSummary {
  id: string;
  name: string;
  category: ResourceCategory;
  locationLabel: string;
  stage: ResourceStage[];
  fitBadge: "High match" | "Good match" | "Explore";
  lastVerifiedIso: string;
}

export interface ResourceDetail extends ResourceSummary {
  description: string;
  sourceUrl: string;
  nextStep: string;
  tags: string[];
}

