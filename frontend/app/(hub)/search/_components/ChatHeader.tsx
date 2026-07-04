"use client";

export default function ChatHeader() {
  return (
    <header className="flex justify-between items-center w-full px-4 md:px-8 py-4 bg-surface/80 backdrop-blur-md sticky top-0 z-10 border-b border-outline-variant">
      <div className="flex items-center gap-4">
        <div>
          <h2
            className="font-[family-name:var(--font-plus-jakarta)] font-bold text-primary"
            style={{ fontSize: "28px", lineHeight: "36px" }}
          >
            Chat Interface
          </h2>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            <span className="text-on-surface-variant" style={{ fontSize: "11px", fontWeight: 500, letterSpacing: "0.5px" }}>
              LeadGen Agent Active
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
