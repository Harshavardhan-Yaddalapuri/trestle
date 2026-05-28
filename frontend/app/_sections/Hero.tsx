"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Hero() {
  return (
    <section className="max-w-[1440px] mx-auto px-4 md:px-8 grid grid-cols-1 md:grid-cols-12 gap-6 items-center min-h-[80vh]">
      <div className="md:col-span-6 flex flex-col items-start gap-8">
        <h1
          className="font-[family-name:var(--font-plus-jakarta)] text-on-surface font-bold"
          style={{ fontSize: "clamp(28px, 4vw, 45px)", lineHeight: "1.15" }}
        >
          Get out of the weeds and have AI agents support your path forward
        </h1>

        <p className="text-on-surface-variant w-full max-w-lg" style={{ fontSize: "16px", lineHeight: "24px", letterSpacing: "0.5px" }}>
          Automated agents that find leads, track events, and research trends
          while you focus on building. Trestle connects your workflows with
          intelligent bridge-builders.
        </p>

        <Button asChild size="lg" className="rounded-full px-12 py-4 h-auto font-bold">
          <Link href="/search">
            Try Trestle
            <span className="material-symbols-outlined">arrow_forward</span>
          </Link>
        </Button>

      </div>

      <div className="md:col-span-6 relative h-[400px] md:h-[600px] w-full flex items-center justify-center">
        <div className="w-full h-full relative p-6">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            alt="Agent network scanning global resources in real time"
            className="w-full h-full object-cover rounded-xl shadow-lg"
            src="/images/AmericaCenteredRadar.png"
            /*src="/images/Scanning_Globe.png"*/
          />
        </div>
      </div>
    </section>
  );
}
