"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Nav() {
  return (
    <nav className="fixed top-0 z-50 w-full bg-surface/80 backdrop-blur-md">
      <div className="flex justify-between items-center w-full px-4 md:px-8 py-4 max-w-[1440px] mx-auto">
        <div className="flex items-center gap-8">
          <Link
            href="/"
            className="font-[family-name:var(--font-plus-jakarta)] tracking-tight font-bold text-primary"
            style={{ fontSize: "28px", lineHeight: "36px" }}
          >
            TRESTLE
          </Link>

          <div className="hidden md:flex gap-6 items-center">
            <Link href="/" className="text-primary border-b-2 border-primary font-bold pb-1 transition-colors duration-200">
              Platform
            </Link>
            <Link href="/dashboard" className="text-on-surface-variant font-medium hover:text-primary transition-colors duration-200">
              Hub
            </Link>
            <Link href="/search" className="text-on-surface-variant font-medium hover:text-primary transition-colors duration-200">
              Agents
            </Link>
            <Link href="#pricing" className="text-on-surface-variant font-medium hover:text-primary transition-colors duration-200">
              Pricing
            </Link>
            <Link href="#community" className="text-on-surface-variant font-medium hover:text-primary transition-colors duration-200">
              Community
            </Link>
          </div>
        </div>

        <Button asChild className="rounded-full font-bold">
          <Link href="/search">Start Building</Link>
        </Button>
      </div>
    </nav>
  );
}
