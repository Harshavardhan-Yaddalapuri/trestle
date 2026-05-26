"use client";

import { useState } from "react";
import type { AlertFrequency, UserSettings } from "@/lib/domain/settings";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const frequencies: { value: AlertFrequency; label: string }[] = [
  { value: "immediate", label: "Immediate" },
  { value: "daily", label: "Daily digest" },
  { value: "weekly", label: "Weekly summary" },
];

export default function SettingsForm({ initial }: { initial: UserSettings }) {
  const [settings, setSettings] = useState(initial);
  const [saved, setSaved] = useState(false);

  function patchNotifications(partial: Partial<UserSettings["notifications"]>) {
    setSettings((s) => ({
      ...s,
      notifications: { ...s.notifications, ...partial },
    }));
    setSaved(false);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaved(true);
  }

  const n = settings.notifications;

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {saved && (
        <p
          className="rounded-lg bg-secondary-container text-on-secondary-container px-4 py-3 text-sm"
          role="status"
        >
          Preferences kept in this session only until a settings API exists.
        </p>
      )}

      <Card className="border-outline-variant shadow-none bg-surface-container-lowest">
        <CardHeader>
          <CardTitle className="font-[family-name:var(--font-plus-jakarta)]">Notifications</CardTitle>
          <CardDescription>Channels and alert cadence for grant deadlines and matches.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <ToggleRow
            id="email"
            label="Email alerts"
            description="Deadlines and high-confidence matches."
            checked={n.emailAlerts}
            onChange={(v) => patchNotifications({ emailAlerts: v })}
          />
          <ToggleRow
            id="inapp"
            label="In-app alerts"
            description="Bell feed inside Trestle Hub."
            checked={n.inAppAlerts}
            onChange={(v) => patchNotifications({ inAppAlerts: v })}
          />
          <ToggleRow
            id="digest"
            label="Weekly digest"
            description="Curated roundup of new programs."
            checked={n.weeklyDigest}
            onChange={(v) => patchNotifications({ weeklyDigest: v })}
          />

          <div className="space-y-2">
            <Label className="text-base">Alert frequency</Label>
            <p className="text-xs text-on-surface-variant">
              How often to batch non-critical reminders (mock control).
            </p>
            <div className="flex flex-wrap gap-2 pt-1">
              {frequencies.map((f) => (
                <button
                  key={f.value}
                  type="button"
                  onClick={() => patchNotifications({ alertFrequency: f.value })}
                  className={`rounded-full border px-4 py-2 text-sm font-medium transition-colors ${
                    n.alertFrequency === f.value
                      ? "bg-secondary-container text-on-secondary-container border-transparent"
                      : "border-outline-variant text-on-surface-variant hover:bg-surface-variant/60"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-outline-variant shadow-none bg-surface-container-lowest">
        <CardHeader>
          <CardTitle className="font-[family-name:var(--font-plus-jakarta)]">Account</CardTitle>
          <CardDescription>Authentication provider TBD — placeholders only.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" disabled>
            Change email
          </Button>
          <Button type="button" variant="outline" disabled>
            Change password
          </Button>
          <Button type="button" variant="destructive" disabled>
            Delete account
          </Button>
        </CardContent>
      </Card>

      <Button type="submit">Save settings (preview)</Button>
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
