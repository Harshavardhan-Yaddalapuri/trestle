"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type MainNavItem = { icon: string; label: string; href: string };

export const MAIN_NAV_ITEMS: MainNavItem[] = [
  { icon: "dashboard", label: "Dashboard", href: "/dashboard" },
  { icon: "smart_toy", label: "Agentic Search", href: "/search" },
  { icon: "hub", label: "Connections", href: "/connections" },
  { icon: "bookmarks", label: "Resources", href: "/resources" },
  { icon: "assignment", label: "Grants", href: "/grants" },
  { icon: "person", label: "Profile", href: "/profile" },
  { icon: "settings", label: "Settings", href: "/settings" },
];

const footerNav: { icon: string; label: string; href: string }[] = [
  { icon: "logout", label: "Log Out", href: "#" },
];

function navActive(pathname: string, href: string): boolean {
  if (href === "#") return false;
  if (href === "/search") return pathname.startsWith("/search");
  if (href === "/grants") {
    return pathname === "/grants" || pathname.startsWith("/grants/");
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export interface AppSidebarProps {
  open: boolean;
  onClose: () => void;
}

export default function AppSidebar({ open, onClose }: AppSidebarProps) {
  const pathname = usePathname() || "";

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/30 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          "fixed md:sticky top-0 z-50 h-screen w-[280px] p-4",
          "bg-surface-container-low border-r border-outline-variant",
          "flex flex-col transition-transform duration-300",
          open ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        )}
      >
        <div className="flex flex-col h-full gap-6">
          <button
            type="button"
            onClick={onClose}
            className="self-end p-2 text-on-surface-variant md:hidden"
            aria-label="Close sidebar"
          >
            <span className="material-symbols-outlined">close</span>
          </button>

          <div className="px-4 py-2">
            <Link
              href="/"
              className="font-[family-name:var(--font-plus-jakarta)] text-primary font-bold tracking-tight"
              style={{ fontSize: "28px", lineHeight: "36px" }}
            >
              TRESTLE
            </Link>
            <div className="flex items-center gap-3 mt-4">
              <div
                className="w-10 h-10 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container font-bold text-sm"
                aria-hidden
              >
                NL
              </div>
              <div>
                <p
                  className="font-[family-name:var(--font-plus-jakarta)] text-on-surface"
                  style={{ fontSize: "22px", lineHeight: "28px", fontWeight: 500 }}
                >
                  Founder Hub
                </p>
                <p
                  className="text-on-surface-variant"
                  style={{ fontSize: "14px", fontWeight: 500, letterSpacing: "0.1px" }}
                >
                  Demo workspace
                </p>
              </div>
            </div>
          </div>

          <nav
            className="flex-1 flex flex-col gap-1 overflow-y-auto"
            style={{ scrollbarWidth: "none" }}
          >
            {MAIN_NAV_ITEMS.map((item) => {
              const active = navActive(pathname, item.href);
              const inner = (
                <>
                  <span className="material-symbols-outlined">{item.icon}</span>
                  <span>{item.label}</span>
                </>
              );
              const className = cn(
                "flex items-center gap-4 px-4 py-3 rounded-full transition-all duration-300",
                "text-[14px] font-medium tracking-wide",
                active
                  ? "bg-secondary-container text-on-secondary-container translate-x-1"
                  : "text-on-surface-variant hover:bg-surface-variant/50",
              );
              if (item.href === "#") {
                return (
                  <span key={item.label} className={cn(className, "cursor-not-allowed opacity-60")}>
                    {inner}
                  </span>
                );
              }
              return (
                <Link
                  key={item.label}
                  href={item.href}
                  className={className}
                  onClick={() => onClose()}
                >
                  {inner}
                </Link>
              );
            })}
          </nav>

          <div className="px-2">
            <Button className="w-full py-4 rounded-xl gap-2 h-auto" type="button" variant="secondary">
              <span className="material-symbols-outlined">add</span>
              Deploy New Agent
            </Button>
          </div>

          <nav className="flex flex-col gap-1 border-t border-outline-variant pt-4 pb-2">
            {footerNav.map((item) => (
              <span
                key={item.label}
                className="text-on-surface-variant flex items-center gap-4 px-4 py-3 rounded-full opacity-60 cursor-not-allowed text-[14px] font-medium tracking-wide"
              >
                <span className="material-symbols-outlined">{item.icon}</span>
                <span>{item.label}</span>
              </span>
            ))}
          </nav>
        </div>
      </aside>
    </>
  );
}
