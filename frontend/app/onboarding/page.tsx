"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { apiClient, type SSEEvent } from "@/lib/api";

interface OnboardingMessage {
  role: "agent" | "user";
  text: string;
  options?: Array<{ label: string; value: string } | string>;
  thinking?: boolean;
}

const PROFILE_FIELDS = [
  "founder_name",
  "company_name",
  "industry",
  "company_stage",
  "location",
  "funding_target_usd_cents",
  "one_liner",
];

export default function OnboardingPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<OnboardingMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [profileComplete, setProfileComplete] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<(() => void) | null>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input when not loading
  useEffect(() => {
    if (!loading) {
      inputRef.current?.focus();
    }
  }, [loading]);

  // Cleanup abort on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.();
    };
  }, []);

  // Check profile completeness from backend
  const checkProfile = useCallback(async () => {
    try {
      const profile = await apiClient.getProfile();
      const filled = PROFILE_FIELDS.filter((key) => {
        const val = (profile as unknown as Record<string, unknown>)[key];
        return (
          val !== null &&
          val !== undefined &&
          val !== "" &&
          !(Array.isArray(val) && val.length === 0)
        );
      }).length;
      const pct = Math.min(100, Math.round((filled / PROFILE_FIELDS.length) * 100));
      setProgress(pct);
      setProfileComplete(filled >= 4);
    } catch (err) {
      console.error("Profile check failed:", err);
    }
  }, []);

  // Initial agent greeting on first load
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([
        {
          role: "agent",
          text: "Hi! I'm Trestle, your AI-powered grant discovery assistant. I see you just signed up — welcome! Let's get your founder profile set up so I can find the best grants, accelerators, and non-dilutive funding for you. What's your name, and what's your startup called?",
          thinking: false,
        },
      ]);
    }
  }, [messages.length]);

  // Periodically check profile so progress updates even while user is reading
  useEffect(() => {
    const id = setInterval(() => {
      if (!loading) checkProfile();
    }, 3000);
    return () => clearInterval(id);
  }, [loading, checkProfile]);

  const handleSend = useCallback(
    async (text: string) => {
      if (abortRef.current) {
        abortRef.current();
        abortRef.current = null;
      }

      setMessages((prev) => [...prev, { role: "user", text }]);
      setInputValue("");
      setLoading(true);

      let streamedText = "";
      let streamedOptions: Array<{ label: string; value: string } | string> | undefined;
      let toolCallsActive = 0;

      const abort = apiClient.chatStream(
        { content: text, conversation_id: conversationId },
        {
          onOpen: () => {},
          onMessage: (event: SSEEvent) => {
            if (event.event === "job_started") {
              const data = event.data as { job_id: string; conversation_id: string };
              setConversationId(data.conversation_id);
              return;
            }

            if (event.event === "token") {
              const data = event.data as { delta: string };
              streamedText += data.delta;
              updateAgentMessage(streamedText, streamedOptions, toolCallsActive > 0);
              return;
            }

            if (event.event === "tool_call") {
              toolCallsActive += 1;
              const data = event.data as { name: string; args: unknown };
              streamedText += `\n\n⧖ Calling tool: **${data.name}**...`;
              updateAgentMessage(streamedText, streamedOptions, true);
              return;
            }

            if (event.event === "tool_result") {
              toolCallsActive = Math.max(0, toolCallsActive - 1);
              const data = event.data as { name: string; result: unknown };
              streamedText += `\n✓ **${data.name}** completed.`;
              updateAgentMessage(streamedText, streamedOptions, toolCallsActive > 0);
              return;
            }

            if (event.event === "question_suggested") {
              const data = event.data as {
                field: string;
                question: string;
                options?: string[];
              };
              streamedOptions = data.options;
              if (!streamedText) {
                streamedText = data.question;
              }
              updateAgentMessage(streamedText, streamedOptions, false);
              return;
            }

            if (event.event === "error") {
              const data = event.data as { code: string; message: string };
              streamedText += `\n\n[Error: ${data.message}]`;
              updateAgentMessage(streamedText, streamedOptions, false);
              return;
            }

            if (event.event === "done") {
              setLoading(false);
              checkProfile();
            }
          },
          onError: (err) => {
            console.error("Chat stream error:", err);
            setMessages((prev) => [
              ...prev,
              {
                role: "agent",
                text: "Something went wrong. Please try again in a moment.",
                thinking: false,
              },
            ]);
            setLoading(false);
          },
          onClose: () => {
            setLoading(false);
            checkProfile();
          },
        }
      );

      abortRef.current = abort;

      function updateAgentMessage(
        text: string,
        options?: Array<{ label: string; value: string } | string>,
        isThinking?: boolean
      ) {
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "agent") {
            return [
              ...prev.slice(0, -1),
              { role: "agent", text, options, thinking: isThinking },
            ];
          }
          return [...prev, { role: "agent", text, options, thinking: isThinking }];
        });
      }
    },
    [conversationId, checkProfile]
  );

  const handleOptionSelect = useCallback(
    (value: string) => {
      if (!loading) handleSend(value);
    },
    [handleSend, loading]
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      const trimmed = inputValue.trim();
      if (trimmed && !loading) {
        handleSend(trimmed);
      }
    }
  };

  return (
    <div className="flex flex-col h-screen bg-surface overflow-hidden">
      {/* Header */}
      <header className="px-6 py-4 border-b border-outline-variant/30 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-secondary text-on-secondary flex items-center justify-center">
            <span className="material-symbols-outlined" style={{ fontSize: "18px" }}>
              psychology
            </span>
          </div>
          <div>
            <h1 className="font-bold text-on-surface" style={{ fontSize: "16px", fontWeight: 600 }}>
              Trestle Onboarding
            </h1>
            <p className="text-on-surface-variant" style={{ fontSize: "12px", fontWeight: 500 }}>
              Let's build your founder profile
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Progress bar */}
          <div className="w-32 h-2 bg-surface-container-high rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="text-on-surface-variant" style={{ fontSize: "12px", fontWeight: 500 }}>
            {progress}%
          </span>
          {profileComplete && (
            <button
              onClick={() => router.push("/search")}
              className="bg-primary text-on-primary px-4 py-2 rounded-full hover:opacity-90 active:scale-95 transition-transform"
              style={{ fontSize: "14px", fontWeight: 600 }}
            >
              Start Exploring →
            </button>
          )}
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 md:px-6 py-6 flex flex-col gap-5 max-w-[720px] mx-auto w-full">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "agent" && (
              <div className="flex items-start gap-3 max-w-[85%]">
                <div className="w-8 h-8 rounded-full bg-secondary text-on-secondary flex items-center justify-center shrink-0 mt-1">
                  <span className="material-symbols-outlined" style={{ fontSize: "18px" }}>
                    psychology
                  </span>
                </div>
                <div className="bg-surface-container-low border border-outline-variant px-5 py-4 rounded-3xl rounded-tl-none">
                  <p
                    className="whitespace-pre-wrap"
                    style={{ fontSize: "16px", lineHeight: "24px", letterSpacing: "0.5px" }}
                  >
                    {msg.text}
                  </p>

                  {msg.options && msg.options.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-3">
                      {msg.options.map((opt, idx) => {
                        const label = typeof opt === "string" ? opt : opt.label;
                        const value = typeof opt === "string" ? opt : opt.value;
                        return (
                          <button
                            key={idx}
                            onClick={() => handleOptionSelect(value)}
                            disabled={loading}
                            className="bg-surface-container-highest text-on-surface px-4 py-2 rounded-full hover:bg-primary-container transition-colors border border-outline-variant disabled:opacity-50"
                            style={{ fontSize: "14px", fontWeight: 500 }}
                          >
                            {label}
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {msg.thinking && (
                    <div className="mt-3 flex items-center gap-3">
                      <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                      <p className="text-on-surface-variant" style={{ fontSize: "14px", fontWeight: 500 }}>
                        Working...
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {msg.role === "user" && (
              <div className="bg-primary-container text-on-primary-container px-5 py-3 rounded-3xl rounded-tr-none max-w-[80%] shadow-sm">
                <p style={{ fontSize: "16px", lineHeight: "24px", letterSpacing: "0.5px" }}>
                  {msg.text}
                </p>
              </div>
            )}
          </div>
        ))}

        {/* Loading indicator when last message is from user */}
        {loading && messages[messages.length - 1]?.role === "user" && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-secondary text-on-secondary flex items-center justify-center shrink-0">
              <span className="material-symbols-outlined" style={{ fontSize: "18px" }}>
                psychology
              </span>
            </div>
            <div className="bg-surface-container-low border border-outline-variant px-4 py-3 rounded-2xl rounded-tl-none flex items-center gap-3">
              <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              <p className="text-on-surface-variant" style={{ fontSize: "14px", fontWeight: 500 }}>
                Thinking...
              </p>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <footer className="p-4 md:px-6 md:pb-8 bg-surface border-t border-outline-variant/30 shrink-0">
        <div className="max-w-[720px] mx-auto relative">
          <div className="flex items-end gap-3 bg-surface-container-highest rounded-[28px] p-2 pr-3 shadow-sm border border-transparent focus-within:border-primary transition-all">
            <input
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1 bg-transparent border-none focus:ring-0 py-3 px-2 text-on-surface placeholder:text-on-surface-variant/60"
              style={{ fontSize: "16px", lineHeight: "24px" }}
              placeholder="Type your answer..."
              disabled={loading}
            />
            <button
              onClick={() => {
                const trimmed = inputValue.trim();
                if (trimmed && !loading) handleSend(trimmed);
              }}
              disabled={loading || !inputValue.trim()}
              className="w-12 h-12 bg-primary text-on-primary rounded-full flex items-center justify-center hover:opacity-90 active:scale-90 transition-transform disabled:opacity-50"
              aria-label="Send"
            >
              <span className="material-symbols-outlined">send</span>
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
