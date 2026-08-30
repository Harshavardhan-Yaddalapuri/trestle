import type { ProfileOut } from "@/lib/api";
import { blankProfile } from "@/lib/profile-readiness";
import { serverRequest } from "@/lib/api/server";
import ProfileForm from "./_components/ProfileForm";

export const metadata = {
  title: "Profile — Trestle",
};

export default async function ProfilePage() {
  let profile: ProfileOut;
  try {
    profile = await serverRequest<ProfileOut>("/api/users/profile");
  } catch {
    profile = blankProfile();
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
      <ProfileForm initial={profile} />
    </div>
  );
}
