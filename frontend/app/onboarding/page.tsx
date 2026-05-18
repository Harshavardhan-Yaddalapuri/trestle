"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { ArrowRight, Loader2 } from "lucide-react";

const STEPS = [
  { field: "name", question: "What's your name?", type: "text" },
  { field: "location", question: "What city are you building in?", type: "text" },
  { field: "state", question: "What state?", type: "select", options: ["Michigan", "Illinois", "Ohio", "Wisconsin", "Other"] },
  { field: "stage", question: "What stage is your startup at?", type: "select", options: ["Idea", "Pre-revenue", "Seed", "Series A", "Growth"] },
  { field: "industry", question: "What industries or technologies? (comma separated)", type: "text" },
  { field: "funding_need", question: "What support are you looking for? (comma separated)", type: "text" },
  { field: "goals", question: "What's your biggest goal in the next 6 months?", type: "text" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [current, setCurrent] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (!data.session) router.push("/login");
    });
  }, [router]);

  async function next() {
    if (!current.trim()) return;
    const s = STEPS[step];
    setAnswers((prev) => ({ ...prev, [s.field]: current }));

    if (step >= STEPS.length - 1) {
      setLoading(true);
      const all = { ...answers, [s.field]: current };
      // Patch profile via API
      const token = (await supabase.auth.getSession()).data.session?.access_token;
      await fetch("/api/profiles/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name: all.name,
          location: all.location,
          state: all.state,
          stage: all.stage?.toLowerCase().replace(" ", "-"),
          industry: all.industry?.split(",").map((s) => s.trim().toLowerCase()),
          funding_need: all.funding_need,
          goals: all.goals,
        }),
      });
      router.push("/dashboard");
      return;
    }

    setStep((p) => p + 1);
    setCurrent("");
  }

  const s = STEPS[step];

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface px-4">
      <div className="w-full max-w-md">
        <div className="mb-2 text-center">
          <span className="text-sm font-medium text-primary">Step {step + 1} of {STEPS.length}</span>
        </div>
        <div className="mb-6 h-1 rounded-full bg-surface-container">
          <div
            className="h-1 rounded-full bg-primary transition-all"
            style={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
          />
        </div>

        <h2 className="mb-6 text-2xl font-bold text-on-surface">{s.question}</h2>

        {s.type === "select" ? (
          <div className="grid gap-3">
            {s.options?.map((opt) => (
              <button
                key={opt}
                onClick={() => { setCurrent(opt); }}
                className={`rounded-xl px-4 py-3 text-left text-sm ring-1 transition-all ${
                  current === opt
                    ? "bg-primary text-on-primary ring-primary"
                    : "bg-surface-container text-on-surface ring-outline-variant/50 hover:ring-primary"
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
        ) : (
          <input
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && next()}
            autoFocus
            className="w-full rounded-xl bg-surface-container px-4 py-3 text-sm outline-none ring-1 ring-outline-variant/50 focus:ring-2 focus:ring-primary"
            placeholder="Type your answer..."
          />
        )}

        <button
          onClick={next}
          disabled={!current.trim() || loading}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-full bg-primary py-3 text-sm font-semibold text-on-primary disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <>Next <ArrowRight className="h-4 w-4" /></>}
        </button>
      </div>
    </div>
  );
}
