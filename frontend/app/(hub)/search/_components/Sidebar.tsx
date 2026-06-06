"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

const mainNav = [
  { icon: "dashboard", label: "Dashboard", active: true },
  { icon: "smart_toy", label: "Agent Hub", active: false },
  { icon: "travel_explore", label: "Research", active: false },
  { icon: "hub", label: "Network", active: false },
  { icon: "settings", label: "Settings", active: false },
];

const footerNav = [
  { icon: "help", label: "Support" },
  { icon: "logout", label: "Log Out" },
];

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export default function Sidebar({ open, onClose }: SidebarProps) {
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
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/30 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`
          fixed md:sticky top-0 z-50 h-screen w-[280px] p-4
          bg-surface-container-low border-r border-outline-variant
          flex flex-col transition-transform duration-300
          ${open ? "translate-x-0" : "-translate-x-full"}
          md:translate-x-0
        `}
      >
        <div className="flex flex-col h-full gap-6">
          {/* Close button (mobile only) */}
          <button
            onClick={onClose}
            className="self-end p-2 text-on-surface-variant md:hidden"
            aria-label="Close sidebar"
          >
            <span className="material-symbols-outlined">close</span>
          </button>

          {/* Header */}
          <div className="px-4 py-2">
            <Link
              href="/"
              className="font-[family-name:var(--font-plus-jakarta)] text-primary font-bold tracking-tight"
              style={{ fontSize: "28px", lineHeight: "36px" }}
            >
              TRESTLE
            </Link>
            <div className="flex items-center gap-3 mt-4">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                alt="Founder Profile"
                className="w-10 h-10 rounded-full bg-secondary-container p-1"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuAuw-ratp4RKbj-turS0zUlrRzExSaOY4Aa14NGrO3XaRAjEOBLwhnJgbJ83vkYq8p9oDGv452eyAC__q3SEJYczquMG5lt5Krnar_BR5Fe_N5BIz7ArA0Uil-zMlMs6j2rH7LxzbcgbeQoSOf7jJDml5adWCcZatd26U4jLreW8dBoMgHk10P5rAvK77fW7JCzPZtvdxDMhNDOGZ9VYIj5LhJWWABHMqnlHiheEAmfswUOX1LbJh2CxOXAI1lxvARC3mUOFb67Wrdt"
              />
              <div>
                <p className="font-[family-name:var(--font-plus-jakarta)] text-on-surface" style={{ fontSize: "22px", lineHeight: "28px", fontWeight: 500 }}>
                  Trestle Hub
                </p>
                <p className="text-on-surface-variant" style={{ fontSize: "14px", fontWeight: 500, letterSpacing: "0.1px" }}>
                  Active Agents: 4
                </p>
              </div>
            </div>
          </div>

          {/* Main Nav */}
          <nav className="flex-1 flex flex-col gap-1 overflow-y-auto" style={{ scrollbarWidth: "none" }}>
            {mainNav.map((item) => (
              <a
                key={item.label}
                href="#"
                className={`flex items-center gap-4 px-4 py-3 rounded-full transition-all duration-300 ${
                  item.active
                    ? "bg-secondary-container text-on-secondary-container translate-x-1"
                    : "text-on-surface-variant hover:bg-surface-variant/50"
                }`}
                style={{ fontSize: "14px", fontWeight: 500, letterSpacing: "0.1px" }}
              >
                <span className="material-symbols-outlined">{item.icon}</span>
                <span>{item.label}</span>
              </a>
            ))}
          </nav>

          {/* CTA */}
          <div className="px-2">
            <Button className="w-full py-4 rounded-xl gap-2 h-auto">
              <span className="material-symbols-outlined">add</span>
              Deploy New Agent
            </Button>
          </div>

          {/* Footer Nav */}
          <nav className="flex flex-col gap-1 border-t border-outline-variant pt-4 pb-2">
            {footerNav.map((item) => (
              <a
                key={item.label}
                href="#"
                className="text-on-surface-variant flex items-center gap-4 px-4 py-3 hover:bg-surface-variant/50 rounded-full transition-all duration-300"
                style={{ fontSize: "14px", fontWeight: 500, letterSpacing: "0.1px" }}
              >
                <span className="material-symbols-outlined">{item.icon}</span>
                <span>{item.label}</span>
              </a>
            ))}
          </nav>
        </div>
      </aside>
    </>
  );
}
