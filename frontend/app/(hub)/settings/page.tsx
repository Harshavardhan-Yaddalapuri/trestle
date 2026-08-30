import type { AlertPreferences } from "@/lib/api";
import { serverRequest } from "@/lib/api/server";
import SettingsForm from "./_components/SettingsForm";

export const metadata = {
  title: "Settings — Trestle",
};

export default async function SettingsPage() {
  let preferences: AlertPreferences = {
    deadline_reminders: true,
    new_grant_matches: true,
    check_ins: true,
  };
  try {
    preferences = await serverRequest<AlertPreferences>("/api/users/alert-preferences");
  } catch {
    // Keep useful defaults visible while the API is temporarily unavailable.
  }

  return (
    <div className="p-4 md:p-8 max-w-2xl mx-auto space-y-6">
      <div>
        <h1
          className="font-[family-name:var(--font-plus-jakarta)] text-primary font-bold"
          style={{ fontSize: "28px", lineHeight: "36px" }}
        >
          Settings
        </h1>
        <p className="text-on-surface-variant mt-1 text-sm md:text-base">
          Control the reminders and profile-driven opportunity alerts you receive.
        </p>
      </div>
      <SettingsForm initial={preferences} />
    </div>
  );
}
