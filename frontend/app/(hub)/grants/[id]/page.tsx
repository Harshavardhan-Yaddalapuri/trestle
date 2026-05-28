import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getTrackedGrantDetail } from "@/lib/data/tracked-grants";
import GrantDetailView from "./_components/GrantDetailView";

type PageProps = {
  params: Promise<{ id: string }>;
};

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const grant = await getTrackedGrantDetail(id);
  if (!grant) return { title: "Grant — Trestle" };
  return { title: `${grant.name} — Trestle` };
}

export default async function GrantDetailPage({ params }: PageProps) {
  const { id } = await params;
  const grant = await getTrackedGrantDetail(id);
  if (!grant) notFound();
  return <GrantDetailView grant={grant} />;
}
