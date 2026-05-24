"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const footerLinks = {
  Product: [
    { label: "Features", href: "#features" },
    { label: "Integrations", href: "#" },
    { label: "Pricing", href: "#pricing" },
  ],
  Company: [
    { label: "About", href: "#" },
    { label: "Blog", href: "#" },
    { label: "Careers", href: "#" },
  ],
  Resources: [
    { label: "Documentation", href: `${API_URL}/docs` },
    { label: "Help Center", href: "#" },
    { label: "Status", href: "#status" },
  ],
};

export default function Footer() {
  const [apiStatus, setApiStatus] = useState<"loading" | "ok" | "down">("loading");

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_URL}/health`)
      .then((r) => r.json())
      .then((data) => {
        if (!cancelled) setApiStatus(data.status === "ok" ? "ok" : "down");
      })
      .catch(() => {
        if (!cancelled) setApiStatus("down");
      });
    return () => { cancelled = true; };
  }, []);

  return (
    <footer className="bg-surface-container-lowest py-8 border-t border-outline-variant">
      <div className="max-w-[1440px] mx-auto px-4 md:px-8 flex flex-col md:flex-row justify-between items-start gap-8">
        <div className="flex flex-col gap-4">
          <span
            className="font-[family-name:var(--font-plus-jakarta)] tracking-tight font-bold text-primary"
            style={{ fontSize: "28px", lineHeight: "36px" }}
          >
            TRESTLE
          </span>
          <p className="text-on-surface-variant max-w-xs">
            Connecting builders with the tools they need to reach their goals faster.
          </p>

          <div id="status" className="flex items-center gap-2 mt-1">
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                apiStatus === "ok"
                  ? "bg-primary"
                  : apiStatus === "down"
                  ? "bg-error"
                  : "bg-outline animate-pulse"
              }`}
            />
            <span className="text-on-surface-variant" style={{ fontSize: "11px", fontWeight: 500 }}>
              API {apiStatus === "ok" ? "Online" : apiStatus === "down" ? "Offline" : "Checking..."}
            </span>
          </div>

          <div className="flex gap-4 mt-2">
            <a className="text-on-surface-variant hover:text-primary" href="#">
              <span className="material-symbols-outlined">share</span>
            </a>
            <a className="text-on-surface-variant hover:text-primary" href="#">
              <span className="material-symbols-outlined">alternate_email</span>
            </a>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-8">
          {Object.entries(footerLinks).map(([heading, links]) => (
            <div key={heading} className="flex flex-col gap-2">
              <p className="font-bold text-on-surface">{heading}</p>
              {links.map((link) => (
                <Link
                  key={link.label}
                  href={link.href}
                  className="text-on-surface-variant hover:text-primary"
                  {...(link.href.startsWith("http") ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                >
                  {link.label}
                </Link>
              ))}
            </div>
          ))}
        </div>
      </div>

      <div className="max-w-[1440px] mx-auto px-4 md:px-8 mt-8 pt-6 border-t border-outline-variant text-center md:text-left">
        <p className="text-on-surface-variant" style={{ fontSize: "11px", lineHeight: "16px", letterSpacing: "0.5px", fontWeight: 500 }}>
          &copy; 2024 TRESTLE Automation. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
