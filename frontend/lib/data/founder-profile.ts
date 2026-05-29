import type { FounderProfile } from "@/lib/domain/founder-profile";
import { MOCK_FOUNDER_PROFILE } from "@/lib/data/mock/seed-data";

export async function loadFounderProfile(): Promise<FounderProfile> {
  await Promise.resolve();
  return structuredClone(MOCK_FOUNDER_PROFILE);
}
