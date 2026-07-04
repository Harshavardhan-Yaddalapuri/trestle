import { apiClient } from "@/lib/api";
import type { FounderProfile } from "@/lib/domain/founder-profile";
import ProfileForm from "./_components/ProfileForm";

export const metadata = {
  title: "Profile — Trestle",
};

function apiProfileToForm(p: Awaited<ReturnType<typeof apiClient.getProfile>>): FounderProfile {
  return {
    schemaVersion: 1,
    companyName: p.company_name ?? "",
    companyWebsite: p.website,
    fundingStage: p.company_stage,
    headquarters: p.location,
    industries: p.industry ?? [],
    productSummary: p.goals,
    targetMarket: p.one_liner,
    tractionSummary: null,
    arrOrRevenueBand: p.funding_raised_usd_cents ? `$${(p.funding_raised_usd_cents / 100).toLocaleString()}` : null,
    runwayBand: null,
    fundingGoal: p.funding_target_usd_cents ? `$${(p.funding_target_usd_cents / 100).toLocaleString()}` : null,
    grantTypes: [],
    geographicPreferences: p.location ? [p.location] : [],
    extras: {},
  };
}

function formToApiProfile(form: FounderProfile) {
  return {
    founder_name: form.companyName,
    company_name: form.companyName,
    company_stage: form.fundingStage,
    industry: form.industries,
    location: form.headquarters,
    website: form.companyWebsite,
    one_liner: form.targetMarket,
    goals: form.productSummary,
    funding_raised_usd_cents: null,
    funding_target_usd_cents: null,
    team_size: null,
    has_technical_cofounder: null,
    incorporated: null,
    incorporation_country: null,
    incorporation_state: null,
  };
}

export default async function ProfilePage() {
  let profile: FounderProfile;
  try {
    const apiProfile = await apiClient.getProfile();
    profile = apiProfileToForm(apiProfile);
  } catch {
    // Fallback to blank form if no profile exists yet
    profile = {
      schemaVersion: 1,
      companyName: "",
      companyWebsite: null,
      fundingStage: null,
      headquarters: null,
      industries: [],
      productSummary: null,
      targetMarket: null,
      tractionSummary: null,
      arrOrRevenueBand: null,
      runwayBand: null,
      fundingGoal: null,
      grantTypes: [],
      geographicPreferences: [],
      extras: {},
    };
  }

  async function saveProfile(form: FounderProfile) {
    "use server";
    await apiClient.updateProfile(formToApiProfile(form));
  }

  return (
    <div className="p-4 md:p-8 max-w-3xl mx-auto space-y-6">
      <div>
        <h1
          className="font-[family-name:var(--font-plus-jakarta)] text-primary font-bold"
          style={{ fontSize: "28px", lineHeight: "36px" }}
        >
          Founder profile
        </h1>
        <p className="text-on-surface-variant mt-1 text-sm md:text-base">
          View and edit fields the assistant will use for matching.
        </p>
      </div>
      <ProfileForm initial={profile} onSave={saveProfile} />
    </div>
  );
}
