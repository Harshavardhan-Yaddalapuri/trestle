"use client";

import Link from "next/link";
import { SearchInput } from "@/app/_components/SearchInput";

export default function Hero() {
  return (
    <section className="mx-auto grid max-w-[1440px] items-center gap-12 px-6 py-16 md:grid-cols-2 md:px-8 md:py-24">
      {/* Left: copy */}
      <div className="flex flex-col gap-6">
        <h1 className="font-[family-name:var(--font-plus-jakarta)] text-4xl leading-tight tracking-tight text-on-surface md:text-5xl">
          Get out of the weeds and have AI agents support your path forward
        </h1>
        <p className="max-w-md text-base leading-relaxed text-on-surface-variant">
          Automated agents that find leads, track events, and research trends
          while you focus on building. Trestle connects your workflows with
          intelligent bridge-builders.
        </p>

        <div className="mt-2">
          <SearchInput />
        </div>

        <Link
          href="/search"
          className="mt-2 inline-flex w-fit items-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-medium text-on-primary transition hover:bg-primary-container hover:text-primary"
        >
          Start Building
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="mt-px">
            <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </Link>

        {/* Stats */}
        <div className="mt-6 flex gap-8">
          <div>
            <p className="text-2xl font-semibold text-on-surface">500+</p>
            <p className="text-xs text-on-surface-variant">Active Agents</p>
          </div>
          <div>
            <p className="text-2xl font-semibold text-on-surface">12k+</p>
            <p className="text-xs text-on-surface-variant">Leads Found</p>
          </div>
          <div>
            <p className="text-2xl font-semibold text-on-surface">99.9%</p>
            <p className="text-xs text-on-surface-variant">Uptime</p>
          </div>
        </div>
      </div>

      {/* Right: visual placeholder */}
      <div className="flex items-center justify-center">
        <div className="relative aspect-[4/3] w-full max-w-lg overflow-hidden rounded-[2rem] bg-surface-container shadow-[0_1px_3px_rgba(0,0,0,0.05)]">
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 p-8">
            <div className="rounded-full bg-secondary-container px-4 py-1 text-xs font-medium text-on-secondary-container">
              TRESTLE ANALYTICS
            </div>
            <div className="h-32 w-32 rounded-full border-2 border-dashed border-outline-variant" />
            <p className="text-center text-sm text-on-surface-variant">
              AI-Powered Resource Discovery
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
