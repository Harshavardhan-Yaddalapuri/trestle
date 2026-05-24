"use client";

import Link from "next/link";

const items = [
  { icon: "chat_bubble", label: "Chat", href: "/search", active: true },
  { icon: "psychology", label: "Agents", href: "/search", active: false },
  { icon: "payments", label: "Pricing", href: "#pricing", active: false },
  { icon: "account_circle", label: "Account", href: "#", active: false },
];

export default function MobileNav() {
  return (
    <nav className="fixed bottom-0 left-0 w-full z-50 flex justify-around items-center px-2 py-3 md:hidden bg-surface-container shadow-lg rounded-t-2xl">
      {items.map((item) => (
        <Link
          key={item.label}
          href={item.href}
          className={`flex flex-col items-center justify-center active:scale-90 transition-transform ${
            item.active
              ? "bg-primary-container text-on-primary-container rounded-2xl px-6 py-1"
              : "text-on-surface-variant px-4 py-2"
          }`}
        >
          <span className="material-symbols-outlined">{item.icon}</span>
          <span style={{ fontSize: "11px", lineHeight: "16px", letterSpacing: "0.5px", fontWeight: 500 }}>
            {item.label}
          </span>
        </Link>
      ))}
    </nav>
  );
}
