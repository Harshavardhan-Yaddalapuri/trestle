import Link from "next/link";
import { Button } from "@/components/ui/button";

export const metadata = {
  title: "Sign up — Trestle",
};

export default function SignupPage() {
  return (
    <div className="min-h-screen bg-surface flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-surface-container-lowest rounded-3xl p-8 border border-outline-variant/40">
        <h1
          className="font-[family-name:var(--font-plus-jakarta)] text-primary font-bold"
          style={{ fontSize: "28px", lineHeight: "36px" }}
        >
          Sign up
        </h1>
        <p className="text-on-surface-variant mt-2 text-sm md:text-base">
          Placeholder auth page. Wire this to your auth provider when ready.
        </p>

        <div className="mt-8 space-y-3">
          <Button className="w-full rounded-full font-bold" disabled>
            Create account
          </Button>
          <p className="text-on-surface-variant text-sm">
            Already have an account?{" "}
            <Link href="/login" className="text-primary font-medium hover:underline">
              Login
            </Link>
          </p>
          <p className="text-on-surface-variant text-sm">
            <Link href="/" className="hover:underline">
              Back to home
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

