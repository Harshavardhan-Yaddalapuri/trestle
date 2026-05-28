import type { ResourceDetail, ResourceSummary } from "@/lib/domain/resources";
import { MOCK_RESOURCES } from "@/lib/data/mock/resources";

function toSummary(r: ResourceDetail): ResourceSummary {
  const { description, nextStep, sourceUrl, tags, ...rest } = r;
  void description;
  void nextStep;
  void sourceUrl;
  void tags;
  return rest;
}

export async function listResources(): Promise<ResourceSummary[]> {
  await Promise.resolve();
  return MOCK_RESOURCES.map(toSummary);
}

export async function getResourceDetail(id: string): Promise<ResourceDetail | null> {
  await Promise.resolve();
  return MOCK_RESOURCES.find((r) => r.id === id) ?? null;
}

