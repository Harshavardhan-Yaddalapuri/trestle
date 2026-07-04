"use client";

export default function Features() {
  return (
    <section className="max-w-[1440px] mx-auto px-4 md:px-8 mt-12">
      <div className="text-center mb-8">
        <h2
          className="font-[family-name:var(--font-plus-jakarta)] font-bold text-on-surface"
          style={{ fontSize: "32px", lineHeight: "40px" }}
        >
          The Infrastructure for Growth
        </h2>
        <p className="text-on-surface-variant max-w-2xl mx-auto mt-4">
          Trestle provides the sturdy foundation needed to scale your operations
          through intelligent, autonomous bridge-building.
        </p>
      </div>

      <div className="flex flex-col md:flex-row gap-6" style={{ minHeight: "600px" }}>
        {/* Left: Large card — 66% width on desktop */}
        <div
          className="bg-surface-container-low rounded-2xl p-8 flex flex-col justify-between relative overflow-hidden group"
          style={{ flex: "2 1 0%" }}
        >
          <div className="z-10">
            <h3
              className="font-[family-name:var(--font-plus-jakarta)] font-bold text-on-surface"
              style={{ fontSize: "22px", lineHeight: "28px" }}
            >
              Your founder assistant
            </h3>
            <p className="text-on-surface-variant mt-2 max-w-md">
              Trestle is a personal assistant that learns about your startup through
              natural conversation and proactively surfaces matching opportunities.
            </p>
          </div>

          <div className="mt-8 flex items-end justify-center z-10">
            <div className="w-full max-w-lg aspect-video bg-surface-container rounded-2xl shadow-inner overflow-hidden border border-outline-variant/30 relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                alt="Data visualization dashboard"
                width={640}
                height={360}
                className="w-full h-full object-cover"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuDt-bod8-E3J6RUbIa0RZSuzBDdQYdZ7kEf_q3v1L1sU3yRugo4uZJfwJgr7JXBpMam8Hp0Xs_DbHKgw26-LNcshhZ-ISFzMXj0L3vTTN6MMwSyrGPi25jw1uuNL-FDIg2JU5Sn5vhJegF8sTIOPD9sIdxZq_JZs1Mu4FqtqBNvFDwrbACHgvkhPlgbn06X7iCxaY9e6KvSQro-KKeEBcXydbNmdD4YkjSrqgJGm14-Ad7l9BRSbNuynQz0MH3q5b8g0VQuHoNOW-DO"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-surface-container-low to-transparent" />
            </div>
          </div>

          <div className="absolute -top-10 -right-10 w-40 h-40 bg-primary/10 rounded-full blur-2xl group-hover:bg-primary/20 transition-all" />
        </div>

        {/* Right: Two stacked cards — 33% width on desktop */}
        <div className="flex flex-col gap-6" style={{ flex: "1 1 0%" }}>
          <div className="flex-1 bg-secondary-container rounded-2xl p-8 flex flex-col justify-center gap-4 overflow-hidden">
            <span className="material-symbols-outlined text-on-secondary-container" style={{ fontSize: "48px" }}>
              target
            </span>
            <div>
              <h3
                className="font-[family-name:var(--font-plus-jakarta)] font-bold text-on-secondary-container"
                style={{ fontSize: "22px", lineHeight: "28px" }}
              >
                Matched to your profile
              </h3>
              <p className="text-on-secondary-container/80 mt-2">
                Grants and programs are scored against your stage, industry, location,
                and eligibility—so you spend time on opportunities you can actually win.
              </p>
            </div>
          </div>

          <div className="flex-1 bg-surface-container-highest rounded-2xl p-8 flex flex-col justify-center gap-4 border border-outline-variant/20">
            <span className="material-symbols-outlined text-primary" style={{ fontSize: "48px" }}>
              assignment
            </span>
            <div>
              <h3
                className="font-[family-name:var(--font-plus-jakarta)] font-bold text-on-surface"
                style={{ fontSize: "22px", lineHeight: "28px" }}
              >
                Grant pipeline
              </h3>
              <p className="text-on-surface-variant mt-2">
                Track what you save—from researching and drafting through submitted
                and awarded—so nothing slips past a deadline.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
