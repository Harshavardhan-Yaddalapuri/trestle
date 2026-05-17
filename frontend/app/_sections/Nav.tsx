"use client";

import Link from "next/link";

export default function Nav() {
  return (
    <header className="sticky top-0 z-50 bg-surface/80 backdrop-blur-md">
      <nav className="mx-auto flex max-w-[1440px] items-center justify-between px-6 py-4 md:px-8">
        {/* Logo */}
        <Link href="/" className="text-xl font-semibold tracking-tight text-primary">
          TRESTLE
        </Link>

        {/* Desktop links */}
        <ul className="hidden items-center gap-8 text-sm font-medium text-on-surface-variant md:flex">
          <li>
            <Link href="/" className="border-b-2 border-primary pb-0.5 text-on-surface">
              Platform
            </Link>
          </li>
          <li><Link href="/search" className="hover:text-on-surface">Agents</Link></li>
          <li><Link href="#pricing" className="hover:text-on-surface">Pricing</Link></li>
          <li><Link href="#contact" className="hover:text-on-surface">Community</Link></li>
        </ul>

        {/* CTA */}
        <Link
          href="/search"
          className="rounded-full bg-primary px-5 py-2 text-sm font-medium text-on-primary transition hover:bg-primary-container hover:text-primary"
        >
          Start Building
        </Link>
      </nav>
    </header>
  );
}
