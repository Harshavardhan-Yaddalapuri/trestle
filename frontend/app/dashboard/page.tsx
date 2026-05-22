"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import {
  Send, Loader2, ArrowLeft, ExternalLink,
  RefreshCw, ShieldCheck, Clock, LayoutDashboard, Search
} from "lucide-react";

type Message = {
  id: string;
  role: "user" | "agent";
  content?: string;
  results?: ResultItem[];
  loading?: boolean;
};

type ResultItem = {
  resource: {
    id: string;
    name: string;
    type: string;
    description: string | null;
    url: string | null;
    deadline: string | null;
    funding_range: string | null;
    location: string[] | null;
  };
  fit_explanation: string;
  next_step: string;
  confidence_badge: string;
  fit_score: number;
  citations: { source: string; url: string; title: string; confidence: string }[];
};

export default function DashboardPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedState, setSelectedState] = useState<string>("Michigan");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (!data.session) router.push("/login");
    });
  }, [router]);

  async function send() {
    if (!input.trim() || loading) return;
    const query = input.trim();
    setInput("");
    const userMsg: Message = { id: Math.random().toString(), role: "user", content: query };
    setMessages((m) => [...m, userMsg]);
    setLoading(true);

    try {
      const token = (await supabase.auth.getSession()).data.session?.access_token;
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ query, state: selectedState, limit: 8 }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      const agentMsg: Message = {
        id: Math.random().toString(),
        role: "agent",
        content: `Found ${data.total_found} results for "${query}". ${data.fresh_sources_scraped > 0 ? `Scraped ${data.fresh_sources_scraped} fresh sources.` : ""}`,
        results: data.results,
      };
      setMessages((m) => [...m, agentMsg]);
    } catch (err: any) {
      setMessages((m) => [
        ...m,
        { id: Math.random().toString(), role: "agent", content: `Error: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-screen bg-surface">
      {/* Sidebar */}
      <aside className="flex w-60 flex-col border-r border-outline-variant/40 bg-surface-low">
        <div className="px-5 pt-5 pb-6">
          <Link href="/" className="text-xl font-bold tracking-tight text-primary">TRESTLE</Link>
        </div>
        <nav className="flex flex-col gap-1 px-3">
          {[
            { icon: LayoutDashboard, label: "Dashboard", active: true },
            { icon: Search, label: "Search History", active: false },
            { icon: RefreshCw, label: "Scout Runs", active: false },
          ].map((item) => (
            <button
              key={item.label}
              className={`flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm transition-all ${
                item.active
                  ? "bg-primary text-on-primary"
                  : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
              }`}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </button>
          ))}
        </nav>
        <div className="mt-auto px-3 pb-5">
          <button
            onClick={() => { supabase.auth.signOut(); router.push("/"); }}
            className="flex w-full items-center gap-3 rounded-xl px-4 py-2.5 text-sm text-on-surface-variant hover:bg-surface-container"
          >
            Sign Out
          </button>
        </div>
      </aside>

      {/* Chat */}
      <div className="flex flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-outline-variant/40 px-6 py-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
            <span className="text-xs font-bold text-primary">T</span>
          </div>
          <div>
            <h1 className="text-sm font-semibold text-on-surface">Trestle Agent</h1>
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-primary" />
              <span className="text-xs text-on-surface-variant">Online — local Ollama</span>
            </div>
          </div>
          <div className="ml-auto flex items-center gap-1">
            {["Michigan", "Illinois"].map((state) => (
              <button
                key={state}
                onClick={() => setSelectedState(state)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-all ${
                  selectedState === state
                    ? "bg-primary text-on-primary"
                    : "bg-surface-container text-on-surface-variant hover:bg-surface-container-high"
                }`}
              >
                {state}
              </button>
            ))}
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-6">
          <div className="mx-auto max-w-3xl flex flex-col gap-6">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <p className="text-lg font-semibold text-on-surface">What are you looking for today?</p>
                <p className="mt-2 max-w-sm text-sm text-on-surface-variant">
                  Ask about grants, accelerators, pitch competitions, or coworking spaces.
                  I&apos;ll check what is still open.
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {[
                    "Grants for pre-revenue founders in Detroit",
                    "Pitch competitions closing soon in Michigan",
                    "Coworking spaces in Ann Arbor",
                    "Accelerator programs for AI startups",
                  ].map((q) => (
                    <button
                      key={q}
                      onClick={() => { setInput(q); }}
                      className="rounded-full bg-surface-container px-4 py-2 text-xs text-on-surface-variant ring-1 ring-outline-variant/40 hover:ring-primary"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <div key={msg.id} className="flex flex-col gap-3">
                {msg.role === "user" ? (
                  <div className="flex justify-end">
                    <div className="max-w-lg rounded-2xl bg-primary px-5 py-3 text-sm text-on-primary">
                      {msg.content}
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col gap-4">
                    <div className="flex items-center gap-2">
                      <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10">
                        <span className="text-xs font-bold text-primary">T</span>
                      </div>
                      <span className="text-xs font-semibold text-on-surface">Trestle Agent</span>
                    </div>

                    <div className="max-w-2xl rounded-2xl bg-surface-container px-5 py-4 text-sm text-on-surface">
                      {msg.content}
                    </div>

                    {msg.results && (
                      <div className="flex flex-col gap-3">
                        {msg.results.map((r) => (
                          <div
                            key={r.resource.id}
                            className="flex flex-col gap-3 rounded-2xl bg-surface-container p-5 ring-1 ring-outline-variant/30"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex flex-col gap-1">
                                <div className="flex items-center gap-2">
                                  <span className="rounded-full bg-primary-container px-2.5 py-0.5 text-xs font-medium text-on-primary-container">
                                    {r.resource.type.replace("_", " ")}
                                  </span>
                                  <span className={`flex items-center gap-1 text-xs ${
                                    r.confidence_badge.includes("Verified") ? "text-primary" : "text-error"
                                  }`}>
                                    {r.confidence_badge.includes("Verified") ? (
                                      <ShieldCheck className="h-3 w-3" />
                                    ) : (
                                      <Clock className="h-3 w-3" />
                                    )}
                                    {r.confidence_badge}
                                  </span>
                                </div>
                                <h3 className="font-semibold text-on-surface">{r.resource.name}</h3>
                              </div>
                              <span className="shrink-0 text-xs font-semibold text-primary">
                                {(r.fit_score * 100).toFixed(0)}% match
                              </span>
                            </div>

                            <p className="text-sm text-on-surface-variant">
                              {r.resource.description || "No description available."}
                            </p>

                            <div className="flex flex-wrap gap-2">
                              {r.resource.location?.map((loc) => (
                                <span key={loc} className="rounded-full bg-surface-high px-2 py-0.5 text-xs text-on-surface-variant">
                                  📍 {loc}
                                </span>
                              ))}
                              {r.resource.deadline && (
                                <span className="rounded-full bg-surface-high px-2 py-0.5 text-xs text-error">
                                  ⏰ {r.resource.deadline}
                                </span>
                              )}
                              {r.resource.funding_range && (
                                <span className="rounded-full bg-surface-high px-2 py-0.5 text-xs text-on-surface-variant">
                                  💰 {r.resource.funding_range}
                                </span>
                              )}
                            </div>

                            <div className="rounded-xl bg-surface-high p-4">
                              <p className="text-sm text-on-surface">
                                <span className="font-medium">Why it fits:</span> {r.fit_explanation}
                              </p>
                              <p className="mt-1 text-sm text-primary">
                                <span className="font-medium">Next step:</span> {r.next_step}
                              </p>
                            </div>

                            {r.citations.length > 0 && (
                              <div className="flex items-center gap-2 text-xs text-on-surface-variant">
                                <span className="font-medium">Source:</span>
                                {r.citations.map((c) => (
                                  <a
                                    key={c.url}
                                    href={c.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-1 text-primary hover:underline"
                                  >
                                    {c.source} <ExternalLink className="h-3 w-3" />
                                  </a>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex items-center gap-2 text-sm text-on-surface-variant">
                <Loader2 className="h-4 w-4 animate-spin" />
                Searching and scraping fresh sources...
              </div>
            )}
            <div ref={endRef} />
          </div>
        </div>

        {/* Input */}
        <div className="border-t border-outline-variant/40 px-6 py-4">
          <form
            onSubmit={(e) => { e.preventDefault(); send(); }}
            className="mx-auto flex max-w-3xl items-center gap-3">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about grants, accelerators, events..."
              className="flex-1 rounded-full bg-surface-container px-5 py-3 text-sm outline-none ring-1 ring-outline-variant/50 focus:ring-2 focus:ring-primary"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-on-primary disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
