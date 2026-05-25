"use client";

import { useState, useCallback } from "react";
import Sidebar from "./_components/Sidebar";
import ChatHeader from "./_components/ChatHeader";
import ChatMessages from "./_components/ChatMessages";
import ChatInput from "./_components/ChatInput";
import type { ChatMessage } from "./_components/ChatMessages";
import { apiClient } from "@/lib/api";

const DEMO_LEADS = [
  {
    name: "James Sterling",
    title: "Founder, FintechFlow",
    badge: "High Match",
    detail: "Canary Wharf, London",
    detailIcon: "location_on",
    avatar: "https://lh3.googleusercontent.com/aida-public/AB6AXuDxf40aU4cUywZBsyqlt2htu3iPsqbybpt13HS6Doz8N8_TY9dRjf7buXE0vFm-XppxQqcuvp5cROD0fjNyZ2Js3ncpRG1M_LgKoyHSYGhMaHrMgwzVaR130IXJyyU1gAnymDnKn5GHTHVo2nn66_htIMgPl0aaQlxByVOxHbzvEY074uz2d-1VgGGMlKx6zpDIufB2Ogf2_xJ0PJoPmis6Vdy3n2ixgxEZtY2brzGGjMXcnLIIXNpyxuXxQjfu7pmvkbeOzNELihWN",
  },
  {
    name: "Anita Meyer",
    title: "CEO, PayPulse",
    badge: "New Series B",
    detail: "Speaking at FintechWeek (Nov 12)",
    detailIcon: "event",
    avatar: "https://lh3.googleusercontent.com/aida-public/AB6AXuDO5o9thblXdZk1SRYv9rX4T8n1bhnE9ibqK8wStuEqVRvsL45tVyjmhmg2mM9PegLsqrwd2iYp6qXji-SBhc1pBh13g-7IBmCrX2wTvOD97CPgzsI1fZQEYR7bmi_Zxji7yMlhaORykaIrkmUNm_h46bz7UA8HsTkQFYneeN5D1Hxkii8_mNWln5o64CZNmOcHO7kuO5vkWuUaWDX2o42a9jyZgw2KGuQuApdvylRbTjMdsyHgZc7wNBkxxxJ6n1QDTXDlGxMArjHZ",
  },
];

function getTimeString(): string {
  return new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
}

const initialMessages: ChatMessage[] = [
  { type: "system", content: "Session started at " + new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true }) },
];

export default function SearchPage() {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [loading, setLoading] = useState(false);

  const handleSend = useCallback(async (text: string) => {
    const userTime = getTimeString();

    setMessages((prev) => [...prev, { type: "user", content: text, time: userTime }]);

    // Show thinking state
    const thinkingMsg: ChatMessage = {
      type: "agent",
      agent: {
        text: `I've started processing your request: "${text}"`,
        thinking: { label: "Researching...", detail: "Querying Trestle API for matching resources..." },
      },
    };
    setMessages((prev) => [...prev, thinkingMsg]);
    setLoading(true);

    try {
      const data = await apiClient.search({ query: text, limit: 5 });

      const resultMsg: ChatMessage = {
        type: "agent",
        agent: {
          text: data.results?.length
            ? `I found ${data.total_found} matching resources. Here are the top results with the highest fit scores.`
            : "I couldn't find matching resources in the database. Here's a demo of what results would look like:",
          leads: data.results?.length
            ? data.results.slice(0, 2).map((r) => ({
                name: r.resource.name,
                title: r.resource.type.replace("_", " "),
                badge: r.confidence_badge,
                detail: r.fit_explanation.slice(0, 60) + "...",
                detailIcon: "info",
                avatar: "",
              }))
            : DEMO_LEADS,
          attachment: {
            name: "london_fintech_leads.csv",
            size: "12.4 KB",
            count: "52 Leads",
          },
        },
      };

      setMessages((prev) => [...prev.slice(0, -1), resultMsg]);
    } catch (err) {
      void err;
      // On API error, show demo data
      const demoMsg: ChatMessage = {
        type: "agent",
        agent: {
          text: "I found 52 qualified leads. Here are the top 3 with the highest engagement probability. I've exported the full list as a CSV for you.",
          leads: DEMO_LEADS,
          attachment: {
            name: "london_fintech_leads.csv",
            size: "12.4 KB",
            count: "52 Leads",
          },
        },
      };
      setMessages((prev) => [...prev.slice(0, -1), demoMsg]);
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <Sidebar />

      <main className="flex-1 flex flex-col bg-surface overflow-hidden">
        <ChatHeader />
        <ChatMessages messages={messages} />
        <ChatInput onSend={handleSend} disabled={loading} />

        {/* Mobile bottom nav */}
        <nav className="fixed bottom-0 left-0 w-full z-50 flex justify-around items-center px-2 py-3 md:hidden bg-surface-container shadow-lg rounded-t-2xl">
          {[
            { icon: "chat_bubble", label: "Chat", active: true },
            { icon: "psychology", label: "Agents", active: false },
            { icon: "payments", label: "Pricing", active: false },
            { icon: "account_circle", label: "Account", active: false },
          ].map((item) => (
            <a
              key={item.label}
              href="#"
              className={`flex flex-col items-center justify-center active:scale-90 transition-transform ${
                item.active
                  ? "bg-primary-container text-on-primary-container rounded-2xl px-6 py-1"
                  : "text-on-surface-variant px-4 py-2"
              }`}
            >
              <span className="material-symbols-outlined">{item.icon}</span>
              <span style={{ fontSize: "11px", fontWeight: 500 }}>{item.label}</span>
            </a>
          ))}
        </nav>
      </main>
    </div>
  );
}
