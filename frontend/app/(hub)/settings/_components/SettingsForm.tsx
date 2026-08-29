"use client";

import { useState } from "react";
import { apiClient, type AlertPreferences } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function SettingsForm({ initial }: { initial: AlertPreferences }) {
  const [preferences, setPreferences] = useState(initial);
  const [status, setStatus] = useState<"idle" | "saved" | "error">("idle");
  const [saving, setSaving] = useState(false);

  function patch(partial: Partial<AlertPreferences>) {
    setPreferences((current) => ({ ...current, ...partial }));
    setStatus("idle");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setStatus("idle");
    try {
      setPreferences(await apiClient.updateAlertPreferences(preferences));
      setStatus("saved");
    } catch {
      setStatus("error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {status === "saved" && (
        <p
          className="rounded-lg bg-secondary-container text-on-secondary-container px-4 py-3 text-sm"
          role="status"
        >
          Alert preferences saved.
        </p>
      )}
      {status === "error" && <p className="rounded-lg bg-error-container text-on-error-container px-4 py-3 text-sm" role="alert">We could not save your alert preferences. Please try again.</p>}

      <Card className="border-outline-variant shadow-none bg-surface-container-lowest">
        <CardHeader>
          <CardTitle className="font-[family-name:var(--font-plus-jakarta)]">Alerts</CardTitle>
          <CardDescription>Choose the opportunity updates that matter to your company.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <ToggleRow
            id="deadlines"
            label="Deadline reminders"
            description="A heads-up before grants you are tracking close."
            checked={preferences.deadline_reminders}
            onChange={(value) => patch({ deadline_reminders: value })}
          />
          <ToggleRow
            id="new-matches"
            label="New grant matches"
            description="Let Trestle notify you when a new opportunity fits your profile."
            checked={preferences.new_grant_matches}
            onChange={(value) => patch({ new_grant_matches: value })}
          />
          <ToggleRow
            id="check-ins"
            label="Application check-ins"
            description="A reminder when a tracked grant has not been updated recently."
            checked={preferences.check_ins}
            onChange={(value) => patch({ check_ins: value })}
          />
        </CardContent>
      </Card>
      <Button type="submit" disabled={saving}>{saving ? "Saving…" : "Save alert preferences"}</Button>
    </form>
  );
}

function ToggleRow({
  id,
  label,
  description,
  checked,
  onChange,
}: {
  id: string;
  label: string;
  description: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4 rounded-lg border border-outline-variant px-3 py-3">
      <div>
        <Label htmlFor={id} className="text-base font-medium text-on-surface">
          {label}
        </Label>
        <p className="text-xs text-on-surface-variant mt-1">{description}</p>
      </div>
      <input
        id={id}
        type="checkbox"
        className="mt-1 h-4 w-4 accent-primary shrink-0"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
    </div>
  );
}
