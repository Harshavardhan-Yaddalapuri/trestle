"use client";

import { useState } from "react";
import Link from "next/link";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
  };

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center px-4">
      <div className="w-full max-w-sm flex flex-col items-center">
        {/* Logo */}
        <Link href="/" className="mb-10 flex flex-col items-center gap-1">
          <span
            className="font-[family-name:var(--font-plus-jakarta)] font-bold text-primary tracking-tight"
            style={{ fontSize: "32px", lineHeight: "40px" }}
          >
            TRESTLE
          </span>
        </Link>

        {/* Card */}
        <div className="w-full bg-surface-container-lowest rounded-3xl p-8" style={{ boxShadow: "0px 1px 3px rgba(0,0,0,0.05)" }}>
          <h2
            className="font-[family-name:var(--font-plus-jakarta)] text-on-surface mb-2"
            style={{ fontSize: "22px", lineHeight: "28px", fontWeight: 500 }}
          >
            Sign in
          </h2>
          <p className="text-on-surface-variant mb-6" style={{ fontSize: "14px", lineHeight: "20px" }}>
            Welcome back. Enter your credentials to continue.
          </p>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {/* Email */}
            <div className="flex flex-col gap-1">
              <label className="text-on-surface-variant" style={{ fontSize: "11px", fontWeight: 500, letterSpacing: "0.5px" }}>
                EMAIL
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="w-full bg-surface-container rounded-xl py-3 px-4 text-on-surface outline-none border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary placeholder:text-on-surface-variant/50 transition-colors"
                style={{ fontSize: "16px", lineHeight: "24px" }}
              />
            </div>

            {/* Password */}
            <div className="flex flex-col gap-1">
              <label className="text-on-surface-variant" style={{ fontSize: "11px", fontWeight: 500, letterSpacing: "0.5px" }}>
                PASSWORD
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-surface-container rounded-xl py-3 px-4 pr-12 text-on-surface outline-none border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary placeholder:text-on-surface-variant/50 transition-colors"
                  style={{ fontSize: "16px", lineHeight: "24px" }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface transition-colors"
                >
                  <span className="material-symbols-outlined" style={{ fontSize: "20px" }}>
                    {showPassword ? "visibility_off" : "visibility"}
                  </span>
                </button>
              </div>
            </div>

            {/* Forgot password */}
            <div className="flex justify-end">
              <Link
                href="#"
                className="text-primary hover:underline"
                style={{ fontSize: "14px", fontWeight: 500 }}
              >
                Forgot password?
              </Link>
            </div>

            {/* Submit */}
            <button
              type="submit"
              className="w-full bg-primary text-on-primary rounded-full py-3 font-bold hover:opacity-90 active:scale-[0.98] transition-all"
              style={{ fontSize: "14px", letterSpacing: "0.1px" }}
            >
              Sign in
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-4 my-6">
            <div className="flex-1 h-px bg-outline-variant" />
            <span className="text-on-surface-variant" style={{ fontSize: "11px", fontWeight: 500, letterSpacing: "0.5px" }}>
              OR
            </span>
            <div className="flex-1 h-px bg-outline-variant" />
          </div>

          {/* OAuth */}
          <div className="flex flex-col gap-3">
            <button className="w-full border border-outline-variant text-on-surface rounded-full py-3 flex items-center justify-center gap-3 hover:bg-surface-container transition-colors" style={{ fontSize: "14px", fontWeight: 500 }}>
              <svg width="18" height="18" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59a14.5 14.5 0 0 1 0-9.18l-7.98-6.19a24.1 24.1 0 0 0 0 21.56l7.98-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>
              Continue with Google
            </button>
            <button className="w-full border border-outline-variant text-on-surface rounded-full py-3 flex items-center justify-center gap-3 hover:bg-surface-container transition-colors" style={{ fontSize: "14px", fontWeight: 500 }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/></svg>
              Continue with GitHub
            </button>
          </div>
        </div>

        {/* Sign up link */}
        <p className="mt-6 text-on-surface-variant" style={{ fontSize: "14px" }}>
          Don&apos;t have an account?{" "}
          <Link href="#" className="text-primary font-medium hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
