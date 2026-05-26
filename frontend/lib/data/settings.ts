import type { UserSettings } from "@/lib/domain/settings";
import { MOCK_USER_SETTINGS } from "@/lib/data/mock/seed-data";

export async function loadUserSettings(): Promise<UserSettings> {
  await Promise.resolve();
  return structuredClone(MOCK_USER_SETTINGS);
}
