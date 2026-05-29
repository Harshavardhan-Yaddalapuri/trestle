"use client";

const logos: { icon: string; name: string }[] = [
  { icon: "hub", name: "CONNECT" },
  { icon: "database", name: "DATASPHERE" },
  { icon: "cloud", name: "NIMBUS" },
  { icon: "shield", name: "SECURE" },
  { icon: "insights", name: "INSIGHTLY" },
  { icon: "electric_bolt", name: "PULSE" },
  { icon: "account_tree", name: "BRIDGEWORKS" },
];

export default function SocialProof() {
  return (
    <section className="max-w-[1440px] mx-auto px-4 md:px-8 mt-12">
      <div className="bg-surface-container-low rounded-2xl border border-outline-variant/40 px-6 py-10 md:px-10">
        <div className="text-center">
          <h2
            className="font-[family-name:var(--font-plus-jakarta)] font-bold text-on-surface"
            style={{ fontSize: "22px", lineHeight: "28px" }}
          >
            Trusted by teams building with agents
          </h2>
          <p className="text-on-surface-variant mt-2 max-w-2xl mx-auto text-sm md:text-base">
            Placeholder social proof. Replace with real customer logos, quotes, or case studies.
          </p>
        </div>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-3 md:gap-4">
          {logos.map((l) => (
            <div
              key={l.name}
              className="flex items-center gap-2 rounded-full border border-outline-variant/50 bg-surface-container-lowest px-4 py-2 text-on-surface-variant"
              style={{ fontSize: "12px", fontWeight: 600, letterSpacing: "0.8px" }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: "18px" }} aria-hidden>
                {l.icon}
              </span>
              <span>{l.name}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

