"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import AppSidebar from "@/components/app-sidebar";
import { cn } from "@/lib/utils";

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

        <main className="flex-1 overflow-y-auto pb-20 md:pb-8">{children}</main>

        <nav className="fixed bottom-0 left-0 right-0 z-30 flex justify-around items-center px-1 py-2 md:hidden bg-surface-container border-t border-outline-variant safe-area-pb">
          {[
            { href: "/dashboard", icon: "dashboard", label: "Home" },
            { href: "/grants", icon: "assignment", label: "Grants" },
            { href: "/search", icon: "smart_toy", label: "Agent" },
            { href: "/profile", icon: "person", label: "Profile" },
          ].map((item) => {
            const active =
              item.href === "/search"
                ? pathname.startsWith("/search")
                : item.href === "/grants"
                  ? pathname.startsWith("/grants")
                  : pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex flex-col items-center justify-center rounded-2xl px-4 py-1 min-w-[4rem] transition-colors",
                  active
                    ? "bg-primary-container text-on-primary-container"
                    : "text-on-surface-variant",
                )}
              >
                <span className="material-symbols-outlined text-[22px]">{item.icon}</span>
                <span className="text-[11px] font-medium">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
