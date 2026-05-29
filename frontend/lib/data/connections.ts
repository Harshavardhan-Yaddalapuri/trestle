import type { ConnectionDetail, ConnectionSummary } from "@/lib/domain/connections";
import { MOCK_CONNECTIONS } from "@/lib/data/mock/connections";

function toSummary(c: ConnectionDetail): ConnectionSummary {
  const { notes, suggestedNextAction, tags, ...rest } = c;
  void notes;
  void suggestedNextAction;
  void tags;
  return rest;
}

export async function listConnections(): Promise<ConnectionSummary[]> {
  await Promise.resolve();
  return MOCK_CONNECTIONS.map(toSummary);
}

export async function getConnectionDetail(id: string): Promise<ConnectionDetail | null> {
  await Promise.resolve();
  return MOCK_CONNECTIONS.find((c) => c.id === id) ?? null;
}

