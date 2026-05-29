"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MAIN_NAV_ITEMS } from "@/components/app-sidebar";
import { cn } from "@/lib/utils";

function isActive(pathname: string, href: string): boolean {
  if (href === "#") return false;
  if (href === "/search") return pathname.startsWith("/search");
  if (href === "/grants") return pathname === "/grants" || pathname.startsWith("/grants/");
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function MobileTrayNav() {
  const pathname = usePathname() || "";

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-30 md:hidden bg-surface-container border-t border-outline-variant safe-area-pb">
      <div className="flex items-center gap-2 px-2 py-2 overflow-x-auto" style={{ scrollbarWidth: "none" }}>
        {MAIN_NAV_ITEMS.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-col items-center justify-center rounded-2xl px-4 py-1 min-w-[4.5rem] shrink-0 transition-colors",
                active ? "bg-primary-container text-on-primary-container" : "text-on-surface-variant",
              )}
            >
              <span className="material-symbols-outlined text-[22px]">{item.icon}</span>
              <span className="text-[11px] font-medium text-center leading-tight">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

