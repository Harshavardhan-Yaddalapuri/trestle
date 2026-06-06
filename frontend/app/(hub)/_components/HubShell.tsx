"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import AppSidebar from "@/components/app-sidebar";
import MobileTrayNav from "@/components/mobile-tray-nav";

export default function HubShell({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pathname = usePathname() || "";

  return (
    <div className="flex h-screen w-full overflow-hidden bg-surface">
      <AppSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="flex items-center gap-3 px-4 py-3 border-b border-outline-variant bg-surface/90 backdrop-blur-md shrink-0 md:px-8">
          <button
            type="button"
            className="md:hidden text-on-surface p-2 -ml-1 hover:bg-surface-variant rounded-full"
            onClick={() => setSidebarOpen(true)}
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
          <span className="text-on-surface-variant text-xs md:text-sm ml-auto truncate max-w-[50%]">
            {pathname.startsWith("/search") ? "" : "Mock data — connect API when ready"}
          </span>
        </header>

        <main className={`flex-1 ${pathname.startsWith("/search") ? "overflow-hidden flex flex-col pb-0 md:pb-0" : "overflow-y-auto pb-20 md:pb-8"}`}>{children}</main>
        <MobileTrayNav />
      </div>
    </div>
  );
}
