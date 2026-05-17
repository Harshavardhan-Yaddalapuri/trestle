import Link from "next/link";

export default function Footer() {
  return (
    <footer className="bg-surface-container">
      <div className="mx-auto max-w-[1440px] px-6 py-12 md:px-8">
        <div className="mb-8 text-center">
          <span className="font-[family-name:var(--font-plus-jakarta)] text-6xl font-bold tracking-tighter text-on-surface md:text-8xl">
            TRESTLE
          </span>
        </div>
        <div className="flex flex-col items-center justify-between gap-4 border-t border-outline-variant pt-6 text-xs text-on-surface-variant md:flex-row">
          <p>© 2026 TRESTLE Automation. All rights reserved.</p>
          <div className="flex gap-6">
            <Link href="#" className="hover:text-on-surface">Privacy</Link>
            <Link href="#" className="hover:text-on-surface">Terms</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
