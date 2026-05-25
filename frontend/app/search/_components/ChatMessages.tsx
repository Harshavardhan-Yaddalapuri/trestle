"use client";

import { useRef, useEffect } from "react";

interface LeadCard {
  name: string;
  title: string;
  badge: string;
  detail: string;
  detailIcon: string;
  avatar: string;
}

interface AgentMessage {
  text: string;
  thinking?: { label: string; detail: string };
  leads?: LeadCard[];
  attachment?: { name: string; size: string; count: string };
}

interface ChatMessage {
  type: "system" | "user" | "agent";
  content?: string;
  time?: string;
  agent?: AgentMessage;
}

function SystemBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-center">
      <span
        className="bg-surface-container-high px-4 py-1 rounded-full text-on-surface-variant"
        style={{ fontSize: "11px", fontWeight: 500, letterSpacing: "0.5px" }}
      >
        {content}
      </span>
    </div>
  );
}

function UserBubble({ content, time }: { content: string; time?: string }) {
  return (
    <div className="flex flex-col items-end gap-1">
      <div className="bg-primary-container text-on-primary-container px-5 py-3 rounded-3xl rounded-tr-none max-w-[85%] md:max-w-[70%] shadow-sm">
        <p style={{ fontSize: "16px", lineHeight: "24px", letterSpacing: "0.5px" }}>{content}</p>
      </div>
      {time && (
        <span className="text-on-surface-variant mr-2" style={{ fontSize: "11px", fontWeight: 500 }}>
          {time}
        </span>
      )}
    </div>
  );
}

function AgentAvatar() {
  return (
    <div className="w-8 h-8 rounded-full bg-secondary text-on-secondary flex items-center justify-center shrink-0">
      <span className="material-symbols-outlined" style={{ fontSize: "18px" }}>psychology</span>
    </div>
  );
}

function AgentBubble({ agent }: { agent: AgentMessage }) {
  return (
    <div className="flex flex-col items-start gap-1">
      <div className="flex items-center gap-3 mb-2">
        <AgentAvatar />
        <span className="font-bold" style={{ fontSize: "14px", fontWeight: 500, letterSpacing: "0.1px" }}>
          LeadGen Agent
        </span>
      </div>

      <div className="bg-surface-container-low border border-outline-variant text-on-surface px-5 py-4 rounded-3xl rounded-tl-none max-w-full md:max-w-[85%]">
        <p className="mb-4" style={{ fontSize: "16px", lineHeight: "24px", letterSpacing: "0.5px" }}>
          {agent.text}
        </p>

        {/* Thinking indicator */}
        {agent.thinking && (
          <div className="bg-surface-container-highest rounded-xl p-4 flex items-center gap-4">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <div>
              <p className="text-on-surface font-bold" style={{ fontSize: "14px", fontWeight: 500 }}>
                {agent.thinking.label}
              </p>
              <p className="text-on-surface-variant" style={{ fontSize: "11px", fontWeight: 500, letterSpacing: "0.5px" }}>
                {agent.thinking.detail}
              </p>
            </div>
          </div>
        )}

        {/* Lead cards */}
        {agent.leads && agent.leads.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {agent.leads.map((lead) => (
              <div key={lead.name} className="bg-surface-container rounded-2xl p-4 hover:shadow-md transition-shadow">
                <div className="flex justify-between items-start mb-3">
                  <div className="flex gap-3">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img className="w-10 h-10 rounded-lg object-cover" alt={lead.name} src={lead.avatar} />
                    <div>
                      <p className="font-[family-name:var(--font-plus-jakarta)] text-on-surface leading-tight" style={{ fontSize: "22px", lineHeight: "28px", fontWeight: 500 }}>
                        {lead.name}
                      </p>
                      <p className="text-on-surface-variant" style={{ fontSize: "11px", fontWeight: 500 }}>
                        {lead.title}
                      </p>
                    </div>
                  </div>
                  <span className="bg-secondary-container text-on-secondary-container px-2 py-0.5 rounded-full" style={{ fontSize: "11px", fontWeight: 500 }}>
                    {lead.badge}
                  </span>
                </div>
                <div className="flex gap-2 mb-3">
                  <span className="text-primary material-symbols-outlined" style={{ fontSize: "14px" }}>{lead.detailIcon}</span>
                  <span className="text-on-surface-variant" style={{ fontSize: "11px", fontWeight: 500 }}>{lead.detail}</span>
                </div>
                <button className="w-full py-2 bg-surface-container-highest text-primary rounded-xl hover:bg-primary hover:text-on-primary transition-all" style={{ fontSize: "14px", fontWeight: 500 }}>
                  View Profile
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Attachment */}
        {agent.attachment && (
          <div className="mt-4 p-3 bg-surface-bright border border-outline-variant rounded-xl flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary-container text-on-primary-container rounded-lg flex items-center justify-center">
                <span className="material-symbols-outlined">description</span>
              </div>
              <div>
                <p className="font-bold" style={{ fontSize: "14px" }}>{agent.attachment.name}</p>
                <p className="text-on-surface-variant" style={{ fontSize: "11px", fontWeight: 500 }}>
                  {agent.attachment.size} &bull; {agent.attachment.count}
                </p>
              </div>
            </div>
            <button className="p-2 text-primary hover:bg-primary-fixed-dim rounded-full transition-colors">
              <span className="material-symbols-outlined">download</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ChatMessages({ messages }: { messages: ChatMessage[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div
      className="flex-1 overflow-y-auto px-4 md:px-6 py-6 flex flex-col gap-6 max-w-[1000px] mx-auto w-full"
      style={{ scrollbarWidth: "none" }}
      role="log"
      aria-live="polite"
      aria-label="Chat messages"
    >
      {messages.map((msg, i) => {
        if (msg.type === "system") return <SystemBubble key={i} content={msg.content || ""} />;
        if (msg.type === "user") return <UserBubble key={i} content={msg.content || ""} time={msg.time} />;
        if (msg.type === "agent" && msg.agent) return <AgentBubble key={i} agent={msg.agent} />;
        return null;
      })}
      <div ref={bottomRef} />
    </div>
  );
}

export type { ChatMessage, LeadCard, AgentMessage };
