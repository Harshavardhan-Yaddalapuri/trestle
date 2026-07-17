"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import ChatHeader from "./_components/ChatHeader";
import ChatMessages from "./_components/ChatMessages";
import ChatInput from "./_components/ChatInput";
import type { ChatMessage } from "./_components/ChatMessages";
import type { GrantCardData } from "@/lib/api";
import { apiClient, mapGrantToCard } from "@/lib/api";

function getTimeString(): string {
  return new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
}

export default function SearchPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const abortRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    const now = getTimeString();
    setMessages([
      { type: "system", content: `Session started at ${now}` },
      {
        type: "agent",
        agent: {
          text: "Hi, I'm Trestle, your AI-powered grant discovery assistant. Tell me about your startup and what you're looking for, and I'll find grants, accelerators, pitch competitions, and non-dilutive funding that fit your profile. After your first message, I'll check if there's anything else I need to know, like your funding stage or target market, to make sure your profile is complete and your results are spot on.",
          prompts: [
            "I'm looking for grants",
            "Find me accelerators",
            "What pitch competitions are coming up?",
          ],
        },
      },
    ]);
  }, []);

  useEffect(() => {
    return () => {
      abortRef.current?.();
    };
  }, []);

  const handleSend = useCallback(async (text: string) => {
    if (abortRef.current) {
      abortRef.current();
      abortRef.current = null;
    }

    const userTime = getTimeString();
    setMessages((prev) => [...prev, { type: "user", content: text, time: userTime }]);

    const thinkingMsg: ChatMessage = {
      type: "agent",
      agent: {
        text: "",
        thinking: { label: "Researching...", detail: "Querying Trestle for matching grants..." },
      },
    };
    setMessages((prev) => [...prev, thinkingMsg]);
    setLoading(true);

    let streamedText = "";
    const streamedGrants: GrantCardData[] = [];
    const streamedPrompts: string[] = [];
    let streamedQuestion: { field: string; question: string; options?: string[] } | null = null;
    let toolCallsActive = 0;

    const abort = apiClient.chatStream(
      { content: text, conversation_id: conversationId },
      {
        onOpen: () => {},
        onMessage: (event) => {
          if (event.event === "job_started") {
            const data = event.data as { job_id: string; conversation_id: string };
            setConversationId(data.conversation_id);
            return;
          }

          if (event.event === "token") {
            const data = event.data as { delta: string };
            streamedText += data.delta;
            updateAgentMessage(streamedText, streamedGrants, streamedPrompts, streamedQuestion, toolCallsActive > 0);
            return;
          }

          if (event.event === "tool_call") {
            toolCallsActive += 1;
            const data = event.data as { name: string; args: unknown };
            streamedText += `\n\n⧖ Calling tool: **${data.name}**...`;
            updateAgentMessage(streamedText, streamedGrants, streamedPrompts, streamedQuestion, true);
            return;
          }

          if (event.event === "tool_result") {
            toolCallsActive = Math.max(0, toolCallsActive - 1);
            const data = event.data as { name: string; result: unknown };
            streamedText += `\n✓ **${data.name}** completed.`;
            updateAgentMessage(streamedText, streamedGrants, streamedPrompts, streamedQuestion, toolCallsActive > 0);

            if (
              data.name === "grant_search" ||
              data.name === "match_grants" ||
              data.name === "recommend_grants" ||
              data.name === "grants.match.run"
            ) {
              const result = data.result as
                | { grants?: unknown[] }
                | { results?: Array<{ grant: unknown }> }
                | unknown[];
              let grantsRaw: unknown[] = [];
              if (Array.isArray(result)) {
                grantsRaw = result;
              } else if (result && typeof result === "object" && "grants" in result) {
                grantsRaw = (result as { grants: unknown[] }).grants;
              } else if (result && typeof result === "object" && "results" in result) {
                grantsRaw = (result as { results: Array<{ grant: unknown }> }).results.map((r) => r.grant);
              }
              const newCards = grantsRaw
                .filter((g): g is Record<string, unknown> => typeof g === "object" && g !== null)
                .map((g) => mapGrantToCard(g as unknown as import("@/lib/api").GrantSummary))
                .filter((c) => c && c.name);
              if (newCards.length > 0) {
                streamedGrants.push(...newCards);
                updateAgentMessage(streamedText, streamedGrants, streamedPrompts, streamedQuestion, toolCallsActive > 0);
              }
            }
            return;
          }

          if (event.event === "question_suggested") {
            const data = event.data as { field: string; question: string; options?: string[] };
            streamedQuestion = {
              field: data.field,
              question: data.question,
              options: data.options,
            };
            return;
          }

          if (event.event === "error") {
            const data = event.data as { code: string; message: string };
            streamedText += `\n\n[Error: ${data.message}]`;
            updateAgentMessage(streamedText, streamedGrants, streamedPrompts, streamedQuestion, false);
            return;
          }

          if (event.event === "done") {
            setLoading(false);
          }
        },
        onError: (err) => {
          console.error("Chat stream error:", err);
          const errorMsg: ChatMessage = {
            type: "agent",
            agent: {
              text: "Something went wrong. Please try again in a moment.",
              prompts: ["Try again"],
            },
          };
          setMessages((prev) => [...prev.slice(0, -1), errorMsg]);
          setLoading(false);
        },
        onClose: () => {
          setLoading(false);
        },
      }
    );

    abortRef.current = abort;

    function updateAgentMessage(
      text: string,
      grants: GrantCardData[],
      prompts: string[],
      question: typeof streamedQuestion,
      isThinking: boolean,
    ) {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last?.type === "agent" && last.agent) {
          return [
            ...prev.slice(0, -1),
            {
              type: "agent",
              agent: {
                ...last.agent,
                text,
                thinking: isThinking ? { label: "Working...", detail: "Orchestrator is processing your request..." } : undefined,
                grants: grants.length > 0 ? grants : undefined,
                prompts: prompts.length > 0 ? prompts : undefined,
                question: question ?? undefined,
              },
            },
          ];
        }
        return prev;
      });
    }
  }, [conversationId]);

  const handlePromptSelect = useCallback((prompt: string) => {
    handleSend(prompt);
  }, [handleSend]);

  useEffect(() => {
    document.title = "Agentic Search — Trestle";
  }, []);

  return (
    <div className="flex-1 flex flex-col bg-surface overflow-hidden h-full">
      <ChatHeader />
      <ChatMessages messages={messages} onPromptSelect={handlePromptSelect} />
      <ChatInput onSend={handleSend} disabled={loading} />
    </div>
  );
}
