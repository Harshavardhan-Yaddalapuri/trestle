"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient, type ProfileIn } from "@/lib/api";

const STAGES = ["idea", "pre_seed", "seed", "series_a", "series_b_plus", "other"];
const INDUSTRIES = ["ai", "biotech", "climate", "fintech", "healthcare", "saas", "hardware"];
const GOALS = ["investor_access", "hiring", "customer_discovery", "partnerships", "mentorship", "market_learning"];

function moneyToCents(value: string): number | null {
  if (!value.trim()) return null;
  const amount = Number(value.replace(/[$,\s]/g, ""));
  return Number.isFinite(amount) && amount >= 0 ? Math.round(amount * 100) : null;
}

export default function StructuredOnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState<ProfileIn>({ industry: [], goals: "" });
  const [raised, setRaised] = useState("");
  const [target, setTarget] = useState("");

  useEffect(() => {
    apiClient.getProfile().then((profile) => {
      setForm(profile);
      setRaised(profile.funding_raised_usd_cents === null ? "" : String(profile.funding_raised_usd_cents / 100));
      setTarget(profile.funding_target_usd_cents === null ? "" : String(profile.funding_target_usd_cents / 100));
    }).catch(() => {
      // A first-time anonymous session has no profile to hydrate yet.
    }).finally(() => setLoading(false));
  }, []);

  function toggle(field: "industry" | "goals", value: string) {
    const values = field === "industry" ? form.industry ?? [] : (form.goals ?? "").split(",").filter(Boolean);
    const next = values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
    setForm((current) => ({ ...current, [field]: field === "industry" ? next : next.join(",") }));
  }

  async function save(nextStep?: number) {
    setSaving(true);
    setError("");
    try {
      const saved = await apiClient.updateProfile({
        ...form,
        funding_raised_usd_cents: moneyToCents(raised),
        funding_target_usd_cents: moneyToCents(target),
      });
      setForm(saved);
      if (nextStep) setStep(nextStep);
      else router.push("/profile");
    } catch {
      setError("We could not save your profile. Check the required fields and try again.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <main className="mx-auto max-w-2xl p-8 text-on-surface-variant">Loading your profile…</main>;

  return (
    <main className="mx-auto max-w-2xl space-y-6 p-4 md:p-8">
      <header>
        <p className="text-sm font-medium text-primary">Step {step} of 2</p>
        <h1 className="font-[family-name:var(--font-plus-jakarta)] text-3xl font-bold text-primary">Build your founder profile</h1>
        <p className="mt-2 text-on-surface-variant">A few details help Trestle find grants and events worth your time.</p>
      </header>
      <div className="h-2 overflow-hidden rounded-full bg-surface-container"><div className="h-full bg-primary transition-all" style={{ width: `${step * 50}%` }} /></div>
      {error && <p role="alert" className="rounded-xl bg-error-container px-4 py-3 text-sm text-on-error-container">{error}</p>}

      {step === 1 ? (
        <section className="space-y-5 rounded-3xl bg-surface-container-lowest p-6 shadow-sm">
          <Field label="Company name"><input required value={form.company_name ?? ""} onChange={(event) => setForm({ ...form, company_name: event.target.value })} /></Field>
          <Field label="Company stage"><select required value={form.company_stage ?? ""} onChange={(event) => setForm({ ...form, company_stage: event.target.value || null })}><option value="">Choose a stage</option>{STAGES.map((stage) => <option key={stage} value={stage}>{stage.replaceAll("_", " ")}</option>)}</select></Field>
          <Field label="Operating location"><input required placeholder="City, state or country" value={form.location ?? ""} onChange={(event) => setForm({ ...form, location: event.target.value })} /></Field>
          <div><label className="text-sm font-medium">Industries</label><Chips values={form.industry ?? []} options={INDUSTRIES} onToggle={(value) => toggle("industry", value)} /></div>
          <Field label="One-line company description"><textarea maxLength={280} rows={3} placeholder="What are you building and for whom?" value={form.one_liner ?? ""} onChange={(event) => setForm({ ...form, one_liner: event.target.value })} /></Field>
          <button type="button" disabled={saving} onClick={() => save(2)} className="rounded-full bg-primary px-5 py-2.5 text-sm font-medium text-on-primary disabled:opacity-60">{saving ? "Saving…" : "Continue"}</button>
        </section>
      ) : (
        <section className="space-y-5 rounded-3xl bg-surface-container-lowest p-6 shadow-sm">
          <Field label="Team size"><input min={1} type="number" value={form.team_size ?? ""} onChange={(event) => setForm({ ...form, team_size: event.target.value ? Number(event.target.value) : null })} /></Field>
          <Field label="Funding raised (USD, optional)"><input inputMode="decimal" value={raised} onChange={(event) => setRaised(event.target.value)} /></Field>
          <Field label="Funding target (USD, optional)"><input inputMode="decimal" value={target} onChange={(event) => setTarget(event.target.value)} /></Field>
          <Field label="Incorporated?"><select value={form.incorporated === null ? "" : String(form.incorporated)} onChange={(event) => setForm({ ...form, incorporated: event.target.value === "" ? null : event.target.value === "true" })}><option value="">Skip for now</option><option value="true">Yes</option><option value="false">No</option></select></Field>
          <div><label className="text-sm font-medium">What would help most?</label><Chips values={(form.goals ?? "").split(",").filter(Boolean)} options={GOALS} onToggle={(value) => toggle("goals", value)} /></div>
          <div className="flex gap-3"><button type="button" onClick={() => setStep(1)} className="rounded-full bg-surface-container px-5 py-2.5 text-sm font-medium">Back</button><button type="button" disabled={saving} onClick={() => save()} className="rounded-full bg-primary px-5 py-2.5 text-sm font-medium text-on-primary disabled:opacity-60">{saving ? "Saving…" : "Finish profile"}</button></div>
          <p className="text-xs text-on-surface-variant">Regulatory details are optional and can be added later from your profile.</p>
        </section>
      )}
    </main>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="grid gap-2 text-sm font-medium text-on-surface">{label}{children}</label>;
}

function Chips({ values, options, onToggle }: { values: string[]; options: string[]; onToggle: (value: string) => void }) {
  return <div className="mt-2 flex flex-wrap gap-2">{options.map((option) => <button type="button" key={option} onClick={() => onToggle(option)} className={`rounded-full px-3 py-1.5 text-sm capitalize ${values.includes(option) ? "bg-primary text-on-primary" : "bg-surface-container text-on-surface-variant"}`}>{option.replaceAll("_", " ")}</button>)}</div>;
}
