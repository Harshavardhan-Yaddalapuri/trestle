"use client";

import { Check } from "lucide-react";

const plans = [
  {
    name: "SEED",
    price: "$0",
    period: "/mo",
    desc: "Perfect for hobbyists and developers exploring the Trestle agent ecosystem.",
    features: ["1 Active Agent", "Basic Lead Gen", "Community Support"],
    cta: "Start Building",
    popular: false,
  },
  {
    name: "GROWTH",
    price: "$49",
    period: "/mo",
    desc: "Scale your output with multiple agents and priority access to new research modules.",
    features: [
      "5 Active Agents",
      "Advanced Research",
      "Priority Events",
      "Dashboard Analytics",
    ],
    cta: "Get Started",
    popular: true,
  },
  {
    name: "SCALE",
    price: "$199",
    period: "/mo",
    desc: "Industrial-strength infrastructure for deep integration and custom node workflows.",
    features: [
      "Unlimited Agents",
      "Node.js Gateway Integration",
      "1-on-1 Dedicated Support",
    ],
    cta: "Contact Sales",
    popular: false,
  },
];

export default function Pricing() {
  return (
    <section id="pricing" className="mx-auto max-w-[1440px] px-6 py-20 md:px-8">
      <div className="mb-12 text-center">
        <h2 className="font-[family-name:var(--font-plus-jakarta)] text-3xl text-on-surface">
          Choose your growth velocity.
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-sm text-on-surface-variant">
          Scalable agent infrastructure designed for modern engineering teams.
          From solo founders to global enterprises.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {plans.map((p) => (
          <div
            key={p.name}
            className={`relative flex flex-col gap-4 rounded-[1.5rem] p-6 ${
              p.popular
                ? "bg-secondary-container ring-1 ring-primary"
                : "bg-surface-container"
            }`}
          >
            {p.popular && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3 py-1 text-xs font-medium text-on-primary">
                MOST POPULAR
              </span>
            )}
            <div className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
              {p.name}
            </div>
            <div className="flex items-baseline gap-1">
              <span className="text-4xl font-semibold text-on-surface">{p.price}</span>
              <span className="text-sm text-on-surface-variant">{p.period}</span>
            </div>
            <p className="text-sm leading-relaxed text-on-surface-variant">{p.desc}</p>
            <ul className="flex flex-col gap-2">
              {p.features.map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm">
                  <Check className="h-4 w-4 text-primary" />
                  {f}
                </li>
              ))}
            </ul>
            <button
              className={`mt-auto w-full rounded-full py-2.5 text-sm font-medium transition ${
                p.popular
                  ? "bg-primary text-on-primary hover:bg-primary-container hover:text-primary"
                  : "bg-surface-high text-on-surface ring-1 ring-outline hover:bg-surface-container-high"
              }`}
            >
              {p.cta}
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
