"use client";

import Link from "next/link";

export default function ChatHeader() {
  return (
    <header className="flex justify-between items-center w-full px-4 md:px-8 py-4 bg-surface/80 backdrop-blur-md sticky top-0 z-10">
      <div className="flex items-center gap-4">
        <button className="md:hidden text-on-surface">
          <span className="material-symbols-outlined">menu</span>
        </button>
        <div>
          <h2
            className="font-[family-name:var(--font-plus-jakarta)] font-bold text-primary"
            style={{ fontSize: "28px", lineHeight: "36px" }}
          >
            Chat Interface
          </h2>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            <span className="text-on-surface-variant" style={{ fontSize: "11px", fontWeight: 500, letterSpacing: "0.5px" }}>
              LeadGen Agent Active
            </span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 md:gap-4">
        <div className="hidden lg:flex items-center gap-6 mr-6">
          <Link href="/" className="text-primary border-b-2 border-primary font-bold pb-1 transition-colors">
            Platform
          </Link>
          <Link href="/search" className="text-on-surface-variant font-medium hover:text-primary transition-colors">
            Agents
          </Link>
          <a href="#" className="text-on-surface-variant font-medium hover:text-primary transition-colors">
            Pricing
          </a>
        </div>
        <button className="p-2 text-on-surface-variant hover:bg-surface-variant rounded-full transition-colors">
          <span className="material-symbols-outlined">search</span>
        </button>
        <Link
          href="/search"
          className="hidden md:flex bg-primary text-on-primary px-6 py-2 rounded-full hover:opacity-90 active:scale-95 transition-transform"
          style={{ fontSize: "14px", fontWeight: 500 }}
        >
          Start Building
        </Link>
      </div>
    </header>
  );
}
