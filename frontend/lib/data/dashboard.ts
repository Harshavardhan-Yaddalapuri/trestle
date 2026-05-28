import type { DashboardHome } from "@/lib/domain/dashboard";
import { MOCK_DASHBOARD_HOME } from "@/lib/data/mock/seed-data";

export async function loadDashboardHome(): Promise<DashboardHome> {
  await Promise.resolve();
  return MOCK_DASHBOARD_HOME;
}
