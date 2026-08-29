"use client";

import { useState } from "react";
import { apiClient, type ProfileIn, type ProfileOut } from "@/lib/api";
import { getProfileReadiness } from "@/lib/profile-readiness";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const STAGES = ["idea", "pre_seed", "seed", "series_a", "series_b_plus", "other"];
const INDUSTRIES = ["ai", "biotech", "climate", "fintech", "healthcare", "saas", "hardware"];
const GOALS = ["investor_access", "hiring", "customer_discovery", "partnerships", "mentorship", "market_learning"];

function moneyToCents(value: string): number | null {
  const normalized = value.replace(/[$,\s]/g, "");
  if (!normalized) return null;
  const amount = Number(normalized);
  return Number.isFinite(amount) && amount >= 0 ? Math.round(amount * 100) : null;
}

function centsToMoney(value: number | null): string {
  return value === null ? "" : String(value / 100);
}

function goalsToList(value: string | null): string[] {
  return value ? value.split(",").map((goal) => goal.trim()).filter(Boolean) : [];
}

function nullable(value: string): string | null {
  return value.trim() || null;
}

export default function ProfileForm({ initial }: { initial: ProfileOut }) {
  const [profile, setProfile] = useState(initial);
  const [raised, setRaised] = useState(centsToMoney(initial.funding_raised_usd_cents));
  const [target, setTarget] = useState(centsToMoney(initial.funding_target_usd_cents));
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<"idle" | "saved" | "error">("idle");
  const readiness = getProfileReadiness(profile);

  function patch(values: Partial<ProfileOut>) {
    setProfile((current) => ({ ...current, ...values }));
    setStatus("idle");
  }

  function toggleList(field: "industry" | "goals", value: string) {
    const values = field === "industry" ? profile.industry ?? [] : goalsToList(profile.goals);
    const next = values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
    patch(field === "industry" ? { industry: next } : { goals: next.join(",") });
  }

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setStatus("idle");
    const data: ProfileIn = {
      founder_name: nullable(profile.founder_name ?? ""),
      company_name: nullable(profile.company_name ?? ""),
      company_stage: profile.company_stage,
      industry: profile.industry ?? [],
      location: nullable(profile.location ?? ""),
      website: nullable(profile.website ?? ""),
      one_liner: nullable(profile.one_liner ?? ""),
      goals: nullable(profile.goals ?? ""),
      team_size: profile.team_size,
      has_technical_cofounder: profile.has_technical_cofounder,
      funding_raised_usd_cents: moneyToCents(raised),
      funding_target_usd_cents: moneyToCents(target),
      incorporated: profile.incorporated,
      incorporation_country: nullable(profile.incorporation_country ?? ""),
      incorporation_state: nullable(profile.incorporation_state ?? ""),
      regulatory_status: profile.regulatory_status,
    };
    try {
      const saved = await apiClient.updateProfile(data);
      setProfile(saved);
      setRaised(centsToMoney(saved.funding_raised_usd_cents));
      setTarget(centsToMoney(saved.funding_target_usd_cents));
      setStatus("saved");
    } catch {
      setStatus("error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={save} className="space-y-6">
      <Card className="border-0 bg-secondary-container/40 shadow-sm">
        <CardContent className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-medium text-on-surface">Recommendation readiness: {readiness.percent}%</p>
            <p className="text-sm text-on-surface-variant">
              {readiness.missingBasics.length ? `Add ${readiness.missingBasics.join(", ")} for stronger matches.` : "Your core matching profile is ready."}
            </p>
          </div>
          <div className="flex gap-2 text-xs">
            <Readiness label="Grants" ready={readiness.grantsReady} />
            <Readiness label="Events" ready={readiness.eventsReady} />
            <Readiness label="Alerts" ready={readiness.alertsReady} />
          </div>
        </CardContent>
      </Card>
      {status === "saved" && <p role="status" className="rounded-xl bg-secondary-container px-4 py-3 text-sm text-on-secondary-container">Profile saved. Recommendations now use these details.</p>}
      {status === "error" && <p role="alert" className="rounded-xl bg-error-container px-4 py-3 text-sm text-on-error-container">We could not save your profile. Check required fields and try again.</p>}

      <Section title="Founder and company" description="The basics that personalize your workspace.">
        <Field label="Your name"><Input value={profile.founder_name ?? ""} onChange={(event) => patch({ founder_name: event.target.value })} /></Field>
        <Field label="Company name"><Input required value={profile.company_name ?? ""} onChange={(event) => patch({ company_name: event.target.value })} /></Field>
        <Field label="Website (optional)"><Input type="url" placeholder="https://example.com" value={profile.website ?? ""} onChange={(event) => patch({ website: event.target.value })} /></Field>
        <Field label="One-line company description" className="sm:col-span-2"><Textarea maxLength={280} rows={3} placeholder="What are you building and for whom?" value={profile.one_liner ?? ""} onChange={(event) => patch({ one_liner: event.target.value })} /></Field>
      </Section>

      <Section title="Company stage and sector" description="Stage and sector are the strongest starting signals for grants and events.">
        <Field label="Company stage"><select required className="h-10 rounded-md border border-input bg-background px-3 text-sm" value={profile.company_stage ?? ""} onChange={(event) => patch({ company_stage: event.target.value || null })}><option value="">Choose a stage</option>{STAGES.map((stage) => <option key={stage} value={stage}>{stage.replaceAll("_", " ")}</option>)}</select></Field>
        <div className="sm:col-span-2"><Label>Industries</Label><ChipGroup values={profile.industry ?? []} options={INDUSTRIES} onToggle={(value) => toggleList("industry", value)} /></div>
      </Section>

      <Section title="Location and incorporation" description="Location and incorporation rules often determine grant eligibility.">
        <Field label="Operating location"><Input required placeholder="City, state or country" value={profile.location ?? ""} onChange={(event) => patch({ location: event.target.value })} /></Field>
        <Field label="Incorporated?"><select className="h-10 rounded-md border border-input bg-background px-3 text-sm" value={profile.incorporated === null ? "" : String(profile.incorporated)} onChange={(event) => patch({ incorporated: event.target.value === "" ? null : event.target.value === "true" })}><option value="">Not sure yet</option><option value="true">Yes</option><option value="false">No</option></select></Field>
        <Field label="Incorporation country" hint="Two-letter code, e.g. US"><Input maxLength={2} value={profile.incorporation_country ?? ""} onChange={(event) => patch({ incorporation_country: event.target.value.toUpperCase() })} /></Field>
        <Field label="Incorporation state" hint="Optional two-letter code"><Input maxLength={2} value={profile.incorporation_state ?? ""} onChange={(event) => patch({ incorporation_state: event.target.value.toUpperCase() })} /></Field>
      </Section>

      <Section title="Team and funding" description="Optional and private: these details improve eligibility checks; they are not shown to other users.">
        <Field label="Team size"><Input min={1} type="number" value={profile.team_size ?? ""} onChange={(event) => patch({ team_size: event.target.value ? Number(event.target.value) : null })} /></Field>
        <Field label="Technical cofounder"><select className="h-10 rounded-md border border-input bg-background px-3 text-sm" value={profile.has_technical_cofounder === null ? "" : String(profile.has_technical_cofounder)} onChange={(event) => patch({ has_technical_cofounder: event.target.value === "" ? null : event.target.value === "true" })}><option value="">Prefer not to say</option><option value="true">Yes</option><option value="false">No</option></select></Field>
        <Field label="Funding raised (USD)"><Input inputMode="decimal" placeholder="0" value={raised} onChange={(event) => { setRaised(event.target.value); setStatus("idle"); }} /></Field>
        <Field label="Funding target (USD)"><Input inputMode="decimal" placeholder="250000" value={target} onChange={(event) => { setTarget(event.target.value); setStatus("idle"); }} /></Field>
      </Section>

      <Section title="Goals" description="Select outcomes you want events and recommendations to prioritize.">
        <div className="sm:col-span-2"><ChipGroup values={goalsToList(profile.goals)} options={GOALS} onToggle={(value) => toggleList("goals", value)} /></div>
      </Section>

      <Section title="Regulatory details" description="Optional. Add only if regulatory readiness affects the programs you pursue.">
        <Field label="Regulatory status" className="sm:col-span-2"><Textarea rows={2} placeholder="e.g. FDA pathway under evaluation" value={String(profile.regulatory_status?.summary ?? "")} onChange={(event) => patch({ regulatory_status: event.target.value.trim() ? { summary: event.target.value } : {} })} /></Field>
      </Section>
      <Button type="submit" disabled={saving}>{saving ? "Saving…" : "Save profile"}</Button>
    </form>
  );
}

function Section({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return <Card className="border-0 bg-surface-container-lowest shadow-sm"><CardHeader><CardTitle className="font-[family-name:var(--font-plus-jakarta)]">{title}</CardTitle><CardDescription>{description}</CardDescription></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2">{children}</CardContent></Card>;
}

function Field({ label, hint, className, children }: { label: string; hint?: string; className?: string; children: React.ReactNode }) {
  return <div className={`grid gap-2 ${className ?? ""}`}><Label>{label}</Label>{children}{hint && <p className="text-xs text-on-surface-variant">{hint}</p>}</div>;
}

function ChipGroup({ values, options, onToggle }: { values: string[]; options: string[]; onToggle: (value: string) => void }) {
  return <div className="mt-2 flex flex-wrap gap-2">{options.map((option) => <button key={option} type="button" onClick={() => onToggle(option)} className={`rounded-full px-3 py-1.5 text-sm capitalize ${values.includes(option) ? "bg-primary text-on-primary" : "bg-surface-container text-on-surface-variant"}`}>{option.replaceAll("_", " ")}</button>)}</div>;
}

function Readiness({ label, ready }: { label: string; ready: boolean }) {
  return <span className={`rounded-full px-3 py-1.5 ${ready ? "bg-primary text-on-primary" : "bg-surface-container text-on-surface-variant"}`}>{label}</span>;
}
