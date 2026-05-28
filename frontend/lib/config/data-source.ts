/**
 * Switch mock adapters to live API clients when backend contracts are ready.
 */
export type DataSourceMode = "mock" | "api";

export const DATA_SOURCE: DataSourceMode =
  (process.env.NEXT_PUBLIC_DATA_SOURCE as DataSourceMode) || "mock";

export function isMockDataSource(): boolean {
  return DATA_SOURCE === "mock";
}
