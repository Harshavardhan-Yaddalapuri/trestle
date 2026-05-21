"use client";

const partners = [
  { icon: "hub", name: "CONNECT" },
  { icon: "database", name: "DATASPHERE" },
  { icon: "cloud", name: "NIMBUS" },
  { icon: "shield", name: "SECURE" },
];

export default function Trust() {
  return (
    <section className="max-w-[1440px] mx-auto px-4 md:px-8 mt-12 py-12 border-t border-outline-variant">
      <div className="flex flex-col md:flex-row items-center justify-between gap-8">
        <div>
          <h3
            className="font-[family-name:var(--font-plus-jakarta)] font-bold text-on-surface"
            style={{ fontSize: "22px", lineHeight: "28px" }}
          >
            Trusted by Founders Everywhere
          </h3>
          <p className="text-on-surface-variant mt-1" style={{ fontSize: "14px" }}>
            Join thousands of builders using Trestle to automate their heavy lifting.
          </p>
        </div>

        <div className="flex items-center gap-8 flex-wrap">
          {partners.map((p) => (
            <div key={p.name} className="flex items-center gap-2 text-on-surface-variant">
              <span className="material-symbols-outlined" style={{ fontSize: "20px" }}>
                {p.icon}
              </span>
              <span style={{ fontSize: "14px", fontWeight: 500, letterSpacing: "0.5px" }}>
                {p.name}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
