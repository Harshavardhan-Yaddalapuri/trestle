"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface ChatHeaderProps {
  onMenuToggle: () => void;
}

export default function ChatHeader({ onMenuToggle }: ChatHeaderProps) {
  const pathname = usePathname() || "";

  return (
    <header className="flex items-center gap-3 px-4 py-3 border-b border-outline-variant bg-surface/90 backdrop-blur-md sticky top-0 z-10 shrink-0 md:px-8">
      <button
        type="button"
        className="md:hidden text-on-surface p-2 -ml-1 hover:bg-surface-variant rounded-full"
        onClick={onMenuToggle}
        aria-label="Open menu"
      >
        <span className="material-symbols-outlined">menu</span>
      </button>

      <Link
        href="/dashboard"
        className="font-[family-name:var(--font-plus-jakarta)] font-bold text-primary text-lg md:hidden"
      >
        Trestle
      </Link>

      <div className="flex items-center gap-2 ml-auto min-w-0">
        <span className="text-on-surface-variant text-xs md:text-sm truncate">
          {pathname.startsWith("/search") ? "Agentic Search" : ""}
        </span>
        <span className="text-on-surface-variant/60 text-xs md:text-sm hidden sm:inline">
          ·
        </span>
        <span className="text-on-surface-variant text-xs md:text-sm hidden sm:inline truncate">
          Mock data — connect API when ready
        </span>
      </div>
    </header>
  );
}
