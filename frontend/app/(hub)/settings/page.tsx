import { loadUserSettings } from "@/lib/data/settings";
import SettingsForm from "./_components/SettingsForm";

export const metadata = {
  title: "Settings — Trestle",
};

export default async function SettingsPage() {
  const settings = await loadUserSettings();

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
          Notification preferences and account management (UI scaffold; backend pending).
        </p>
      </div>
      <SettingsForm initial={settings} />
    </div>
  );
}
