"use client";

import { useState } from "react";
import Link from "next/link";

export default function SignupPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [agreed, setAgreed] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
  };

  return (
    <div className="min-h-screen bg-surface flex flex-col items-center justify-center px-4 relative overflow-hidden">
      {/* Top-right gradient */}
      <div className="absolute top-0 right-0 w-[600px] h-[400px] bg-gradient-to-bl from-secondary-container/60 via-primary-fixed/20 to-transparent rounded-bl-full pointer-events-none" />

      {/* Logo */}
      <div className="flex flex-col items-center mb-8 z-10">
        <div className="w-14 h-14 rounded-full bg-primary mb-4" />
        <h1
          className="font-[family-name:var(--font-plus-jakarta)] font-bold text-primary tracking-tight"
          style={{ fontSize: "36px", lineHeight: "44px" }}
        >
          TRESTLE
        </h1>
        <p className="text-on-surface-variant text-center mt-2 max-w-xs" style={{ fontSize: "14px", lineHeight: "20px" }}>
          Build the future of autonomous systems with agents that scale.
        </p>
      </div>

      {/* Card */}
      <div className="w-full max-w-md bg-surface-container-lowest rounded-3xl p-8 shadow-sm z-10">
        <h2
          className="font-[family-name:var(--font-plus-jakarta)] text-on-surface mb-6"
          style={{ fontSize: "28px", lineHeight: "36px", fontWeight: 400 }}
        >
          Create your account
        </h2>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          {/* Full Name */}
          <div className="flex flex-col gap-1.5">
            <label className="text-on-surface" style={{ fontSize: "14px", fontWeight: 500 }}>Full Name</label>
            <div className="relative">
              <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant" style={{ fontSize: "20px" }}>
                person
              </span>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="John Doe"
                className="w-full bg-surface-container-high rounded-xl py-3 pl-12 pr-4 text-on-surface outline-none border-none focus:ring-2 focus:ring-primary placeholder:text-on-surface-variant/60"
                style={{ fontSize: "16px" }}
              />
            </div>
          </div>

          {/* Email */}
          <div className="flex flex-col gap-1.5">
            <label className="text-on-surface" style={{ fontSize: "14px", fontWeight: 500 }}>Email Address</label>
            <div className="relative">
              <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant" style={{ fontSize: "20px" }}>
                mail
              </span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="w-full bg-surface-container-high rounded-xl py-3 pl-12 pr-4 text-on-surface outline-none border-none focus:ring-2 focus:ring-primary placeholder:text-on-surface-variant/60"
                style={{ fontSize: "16px" }}
              />
            </div>
          </div>

          {/* Password */}
          <div className="flex flex-col gap-1.5">
            <label className="text-on-surface" style={{ fontSize: "14px", fontWeight: 500 }}>Password</label>
            <div className="relative">
              <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant" style={{ fontSize: "20px" }}>
                lock
              </span>
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-surface-container-high rounded-xl py-3 pl-12 pr-12 text-on-surface outline-none border-none focus:ring-2 focus:ring-primary placeholder:text-on-surface-variant/60"
                style={{ fontSize: "16px" }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface transition-colors"
              >
                <span className="material-symbols-outlined" style={{ fontSize: "20px" }}>
                  {showPassword ? "visibility_off" : "visibility"}
                </span>
              </button>
            </div>
          </div>

          {/* Terms */}
          <div className="flex items-start gap-3">
            <input
              type="checkbox"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
              className="mt-0.5 w-5 h-5 rounded-md border-outline-variant text-primary focus:ring-primary cursor-pointer"
            />
            <span className="text-on-surface-variant" style={{ fontSize: "14px", lineHeight: "20px" }}>
              I agree to the{" "}
              <Link href="#" className="text-primary font-medium hover:underline">Terms of Service</Link>
              {" "}and{" "}
              <Link href="#" className="text-primary font-medium hover:underline">Privacy Policy</Link>.
            </span>
          </div>

          {/* Submit */}
          <button
            type="submit"
            className="w-full bg-primary text-on-primary rounded-xl py-3.5 font-bold flex items-center justify-center gap-2 hover:opacity-90 active:scale-[0.98] transition-all"
            style={{ fontSize: "16px" }}
          >
            Create Account
            <span className="material-symbols-outlined" style={{ fontSize: "20px" }}>arrow_forward</span>
          </button>
        </form>

        {/* Divider */}
        <div className="flex items-center gap-4 my-6">
          <div className="flex-1 h-px bg-outline-variant" />
          <span className="text-on-surface-variant uppercase tracking-widest" style={{ fontSize: "11px", fontWeight: 500 }}>
            or continue with
          </span>
          <div className="flex-1 h-px bg-outline-variant" />
        </div>

        {/* OAuth */}
        <div className="grid grid-cols-2 gap-4">
          <button className="bg-secondary-container/50 text-on-secondary-container rounded-xl py-3 flex items-center justify-center gap-2 hover:bg-secondary-container transition-colors" style={{ fontSize: "14px", fontWeight: 500 }}>
            <span className="material-symbols-outlined" style={{ fontSize: "18px" }}>g_mobiledata</span>
            Google
          </button>
          <button className="bg-secondary-container/50 text-on-secondary-container rounded-xl py-3 flex items-center justify-center gap-2 hover:bg-secondary-container transition-colors" style={{ fontSize: "14px", fontWeight: 500 }}>
            <span className="material-symbols-outlined" style={{ fontSize: "18px" }}>code</span>
            GitHub
          </button>
        </div>
      </div>
    </div>
  );
}
