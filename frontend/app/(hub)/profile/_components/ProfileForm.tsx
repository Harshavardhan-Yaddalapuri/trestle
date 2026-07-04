"use client";

import { useState } from "react";
import type { FounderProfile } from "@/lib/domain/founder-profile";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

function linesToList(s: string): string[] {
  return s
    .split("\n")
    .map((x) => x.trim())
    .filter(Boolean);
}

function listToLines(arr: string[] | null | undefined): string {
  return (arr || []).join("\n");
}

interface ProfileFormProps {
  initial: FounderProfile;
  onSave: (profile: FounderProfile) => Promise<void>;
}

export default function ProfileForm({ initial, onSave }: ProfileFormProps) {
  const [form, setForm] = useState(initial);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function update<K extends keyof FounderProfile>(key: K, value: FounderProfile[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await onSave(form);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save profile");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {saved && (
        <p
          className="rounded-lg bg-secondary-container text-on-secondary-container px-4 py-3 text-sm"
          role="status"
        >
          Profile saved successfully.
        </p>
      )}
      {error && (
        <p className="rounded-lg bg-error-container text-on-error-container px-4 py-3 text-sm" role="alert">
          {error}
        </p>
      )}

      <Card className="border-outline-variant shadow-none bg-surface-container-lowest">
        <CardHeader>
          <CardTitle className="font-[family-name:var(--font-plus-jakarta)]">Company</CardTitle>
          <CardDescription>Basics investors and grant reviewers usually ask for first.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <Field>
            <Label htmlFor="companyName">Company name</Label>
            <Input
              id="companyName"
              value={form.companyName}
              onChange={(e) => update("companyName", e.target.value)}
              required
            />
          </Field>
          <Field>
            <Label htmlFor="website">Website</Label>
            <Input
              id="website"
              value={form.companyWebsite ?? ""}
              onChange={(e) => update("companyWebsite", e.target.value || null)}
              placeholder="https://"
            />
          </Field>
          <Field>
            <Label htmlFor="stage">Funding stage</Label>
            <Input
              id="stage"
              value={form.fundingStage ?? ""}
              onChange={(e) => update("fundingStage", e.target.value || null)}
              placeholder="e.g. pre_seed, seed"
            />
          </Field>
          <Field>
            <Label htmlFor="hq">Headquarters</Label>
            <Input
              id="hq"
              value={form.headquarters ?? ""}
              onChange={(e) => update("headquarters", e.target.value || null)}
            />
          </Field>
          <Field className="sm:col-span-2">
            <Label htmlFor="industries">Industries (one per line)</Label>
            <Textarea
              id="industries"
              rows={3}
              value={listToLines(form.industries)}
              onChange={(e) => update("industries", linesToList(e.target.value))}
            />
          </Field>
        </CardContent>
      </Card>

      <Card className="border-outline-variant shadow-none bg-surface-container-lowest">
        <CardHeader>
          <CardTitle className="font-[family-name:var(--font-plus-jakarta)]">Product & market</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          <Field>
            <Label htmlFor="product">Product summary</Label>
            <Textarea
              id="product"
              rows={3}
              value={form.productSummary ?? ""}
              onChange={(e) => update("productSummary", e.target.value || null)}
            />
          </Field>
          <Field>
            <Label htmlFor="market">Target market</Label>
            <Textarea
              id="market"
              rows={2}
              value={form.targetMarket ?? ""}
              onChange={(e) => update("targetMarket", e.target.value || null)}
            />
          </Field>
          <Field>
            <Label htmlFor="traction">Traction</Label>
            <Textarea
              id="traction"
              rows={2}
              value={form.tractionSummary ?? ""}
              onChange={(e) => update("tractionSummary", e.target.value || null)}
            />
          </Field>
        </CardContent>
      </Card>

      <Card className="border-outline-variant shadow-none bg-surface-container-lowest">
        <CardHeader>
          <CardTitle className="font-[family-name:var(--font-plus-jakarta)]">Financials (bands)</CardTitle>
          <CardDescription>Exact numbers can move to a secured field set later.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <Field>
            <Label htmlFor="arr">Revenue / ARR band</Label>
            <Input
              id="arr"
              value={form.arrOrRevenueBand ?? ""}
              onChange={(e) => update("arrOrRevenueBand", e.target.value || null)}
            />
          </Field>
          <Field>
            <Label htmlFor="runway">Runway band</Label>
            <Input
              id="runway"
              value={form.runwayBand ?? ""}
              onChange={(e) => update("runwayBand", e.target.value || null)}
            />
          </Field>
          <Field className="sm:col-span-2">
            <Label htmlFor="goal">Funding goal</Label>
            <Input
              id="goal"
              value={form.fundingGoal ?? ""}
              onChange={(e) => update("fundingGoal", e.target.value || null)}
            />
          </Field>
        </CardContent>
      </Card>

      <Card className="border-outline-variant shadow-none bg-surface-container-lowest">
        <CardHeader>
          <CardTitle className="font-[family-name:var(--font-plus-jakarta)]">Preferences</CardTitle>
          <CardDescription>Used to rank opportunities in discovery.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <Field>
            <Label htmlFor="grantTypes">Grant types (one per line)</Label>
            <Textarea
              id="grantTypes"
              rows={3}
              value={listToLines(form.grantTypes)}
              onChange={(e) => update("grantTypes", linesToList(e.target.value))}
            />
          </Field>
          <Field>
            <Label htmlFor="geo">Geographic preferences (one per line)</Label>
            <Textarea
              id="geo"
              rows={2}
              value={listToLines(form.geographicPreferences)}
              onChange={(e) => update("geographicPreferences", linesToList(e.target.value))}
            />
          </Field>
        </CardContent>
      </Card>

      <Button type="submit" disabled={saving}>
        {saving ? "Saving…" : "Save profile"}
      </Button>
    </form>
  );
}

function Field({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={`grid gap-2 ${className ?? ""}`}>{children}</div>;
}
