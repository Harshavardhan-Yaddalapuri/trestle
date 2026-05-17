"use client";

import { BarChart3, Bell, Search } from "lucide-react";

const cards = [
  {
    title: "Autonomous Discovery",
    body: "Our agents crawl the web to find leads that match your ideal customer profile with 98% accuracy.",
    icon: Search,
    wide: true,
  },
  {
    title: "Event Tracking",
    body: "Real-time alerts for market changes, competitor moves, and social mentions.",
    icon: BarChart3,
    wide: false,
  },
  {
    title: "Trend Research",
    body: "Deep-dive research agents that compile comprehensive reports on emerging tech trends.",
    icon: Bell,
    wide: false,
  },
];

export default function Features() {
  return (
    <section id="features" className="mx-auto max-w-[1440px] px-6 py-20 md:px-8">
      <div className="mb-12 text-center">
        <h2 className="font-[family-name:var(--font-plus-jakarta)] text-3xl text-on-surface">
          The Infrastructure for Growth
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-sm text-on-surface-variant">
          Trestle provides the sturdy foundation needed to scale your operations
          through intelligent, autonomous bridge-building.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {cards.map((c) => (
          <div
            key={c.title}
            className={`flex flex-col gap-3 rounded-[1.5rem] bg-surface-container p-6 transition hover:shadow-[0_1px_3px_rgba(0,0,0,0.05)] ${
              c.wide ? "md:col-span-2" : ""
            }`}
          >
            <c.icon className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary-container p-2 text-on-secondary-container" />
            <h3 className="font-[family-name:var(--font-plus-jakarta)] text-lg font-medium text-on-surface">
              {c.title}
            </h3>
            <p className="text-sm leading-relaxed text-on-surface-variant">{c.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
