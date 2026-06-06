"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase-client";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [error, setError] = useState("");

  useEffect(() => {
    const hash = window.location.hash;
    const query = new URLSearchParams(window.location.search);

    async function exchange() {
      // Handle magic-link / confirmation token in query
      const code = query.get("code");
      if (code) {
        const { error } = await supabase.auth.exchangeCodeForSession(code);
        if (error) {
          setError(error.message);
          return;
        }
      }

      // Ensure session is present
      const { data } = await supabase.auth.getSession();
      if (data.session) {
        router.push("/onboarding");
      } else {
        setError("Unable to sign in. Please try again.");
      }
    }

    exchange();
  }, [router]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface px-4">
        <div className="max-w-md w-full text-center space-y-4">
          <div className="w-16 h-16 rounded-full bg-error-container text-on-error-container flex items-center justify-center mx-auto">
            <span className="material-symbols-outlined" style={{ fontSize: "32px" }}>error</span>
          </div>
          <h1 className="font-bold text-primary" style={{ fontSize: "24px" }}>Something went wrong</h1>
          <p className="text-on-surface-variant">{error}</p>
          <a href="/auth/login" className="inline-block bg-primary text-on-primary px-6 py-3 rounded-full font-medium hover:opacity-90 transition-opacity">
            Go to login
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
        <p className="text-on-surface-variant font-medium" style={{ fontSize: "16px" }}>Completing sign-in...</p>
      </div>
    </div>
  );
}
