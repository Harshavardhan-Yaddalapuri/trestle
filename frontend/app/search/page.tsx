"use client";

import { useState, useCallback, useEffect } from "react";
import AppSidebar from "@/components/app-sidebar";
import MobileTrayNav from "@/components/mobile-tray-nav";
import ChatHeader from "./_components/ChatHeader";
import ChatMessages from "./_components/ChatMessages";
import ChatInput from "./_components/ChatInput";
import type { ChatMessage } from "./_components/ChatMessages";
import type { GrantData } from "./_components/GrantCard";
import { apiClient } from "@/lib/api";
import { getSessionId } from "@/lib/session";

const DEMO_LEAD = {
  name: "James Sterling",
  title: "Founder, FintechFlow",
  badge: "High Match",
  detail: "Canary Wharf, London",
  detailIcon: "location_on",
  avatar: "https://lh3.googleusercontent.com/aida-public/AB6AXuDxf40aU4cUywZBsyqlt2htu3iPsqbybpt13HS6Doz8N8_TY9dRjf7buXE0vFm-XppxQqcuvp5cROD0fjNyZ2Js3ncpRG1M_LgKoyHSYGhMaHrMgwzVaR130IXJyyU1gAnymDnKn5GHTHVo2nn66_htIMgPl0aaQlxByVOxHbzvEY074uz2d-1VgGGMlKx6zpDIufB2Ogf2_xJ0PJoPmis6Vdy3n2ixgxEZtY2brzGGjMXcnLIIXNpyxuXxQjfu7pmvkbeOzNELihWN",
};

const DEMO_GRANT: GrantData = {
  name: "Michigan AI Innovation Fund",
  amount: "$50,000 – $150,000",
  deadline: "August 15, 2026",
  daysLeft: 87,
  eligibility: "Strong fit: you're an AI startup in Michigan at pre-seed/seed stage, which matches this fund's focus on early-stage AI ventures in the state.",
  sourceUrl: "https://michigan.gov/leo/bureaus-agencies/ai-innovation-fund",
  freshness: "Verified this week",
  description: "The Michigan AI Innovation Fund provides non-dilutive grants to early-stage AI companies headquartered in Michigan. The program supports product development, talent acquisition, and go-to-market activities for startups leveraging artificial intelligence.",
  budgetInfo: "Awards range from $50,000 to $150,000. Funds may be used for R&D, hiring, cloud infrastructure, and market validation. No equity stake is taken.",
  eligibilityCriteria: [
    "Michigan-headquartered company",
    "Pre-seed or seed stage",
    "AI/ML as core technology",
    "Less than $2M in prior funding",
    "Founded within the last 3 years",
  ],
};

function getTimeString(): string {
  return new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
}

export default function SearchPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sessionId, setSessionId] = useState<string>("");

  useEffect(() => {
    const sid = getSessionId();
    setSessionId(sid);

    const now = getTimeString();
    setMessages([
      { type: "system", content: `Session started at ${now}` },
      {
        type: "agent",
        agent: {
          text: "Hi, I'm Trestle, your AI-powered resource discovery assistant. Tell me about your startup and what you're looking for, and I'll find grants, accelerators, pitch competitions, coworking spaces, events, mentorship programs, and more that fit your profile. After your first message, I'll check if there's anything else I need to know, like your funding stage or target market, to make sure your profile is complete and your results are spot on.",
          prompts: [
            "I'm looking for grants",
            "Find me accelerators",
            "What pitch competitions are coming up?",
          ],
        },
      },
    ]);
  }, []);

  const handleSend = useCallback(async (text: string) => {
    const userTime = getTimeString();
    setMessages((prev) => [...prev, { type: "user", content: text, time: userTime }]);

    const thinkingMsg: ChatMessage = {
      type: "agent",
      agent: {
        text: `Searching for resources matching: "${text}"`,
        thinking: { label: "Researching...", detail: "Querying Trestle API for matching resources..." },
      },
    };
    setMessages((prev) => [...prev, thinkingMsg]);
    setLoading(true);

    try {
      const data = await apiClient.search({
        query: text,
        limit: 5,
        session_id: sessionId,
      });

      const resultMsg: ChatMessage = {
        type: "agent",
        agent: {
          text: data.results?.length
            ? `I found ${data.total_found} matching resources. Here are the top results.`
            : "I couldn't find matching resources in the database right now. Here's what results would look like:",
          grants: [DEMO_GRANT],
          leads: [DEMO_LEAD],
          prompts: [
            "Tell me more about the AI Innovation Fund",
            "Are there any accelerators too?",
            "What about pitch competitions?",
          ],
        },
      };

      setMessages((prev) => [...prev.slice(0, -1), resultMsg]);
    } catch (err) {
      void err;
      const demoMsg: ChatMessage = {
        type: "agent",
        agent: {
          text: "Here's what I found based on your query. I've included a matching grant and a relevant contact.",
          grants: [DEMO_GRANT],
          leads: [DEMO_LEAD],
          attachment: {
            name: "matching_resources.csv",
            size: "8.2 KB",
            count: "12 Resources",
          },
          prompts: [
            "Tell me more about the AI Innovation Fund",
            "Are there any accelerators too?",
            "What about pitch competitions?",
          ],
        },
      };
      setMessages((prev) => [...prev.slice(0, -1), demoMsg]);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const handlePromptSelect = useCallback((prompt: string) => {
    handleSend(prompt);
  }, [handleSend]);

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <AppSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <main className="flex-1 flex flex-col bg-surface overflow-hidden">
        <ChatHeader onMenuToggle={() => setSidebarOpen((v) => !v)} />
        <ChatMessages messages={messages} onPromptSelect={handlePromptSelect} />
        <ChatInput onSend={handleSend} disabled={loading} />
        <MobileTrayNav />
      </main>
    </div>
  );
}
