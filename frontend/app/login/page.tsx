import Link from "next/link";
import { Button } from "@/components/ui/button";

export const metadata = {
  title: "Login — Trestle",
};

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-surface flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-surface-container-lowest rounded-3xl p-8 border border-outline-variant/40">
        <h1
          className="font-[family-name:var(--font-plus-jakarta)] text-primary font-bold"
          style={{ fontSize: "28px", lineHeight: "36px" }}
        >
          Login
        </h1>
        <p className="text-on-surface-variant mt-2 text-sm md:text-base">
          Placeholder auth page. Wire this to your auth provider when ready.
        </p>

        <div className="mt-8 space-y-3">
          <Button className="w-full rounded-full font-bold" disabled>
            Continue
          </Button>
          <p className="text-on-surface-variant text-sm">
            Don&apos;t have an account?{" "}
            <Link href="/signup" className="text-primary font-medium hover:underline">
              Sign up
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

