"use client";

import { useState, useRef, useEffect, useCallback } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "48px";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + "px";
    }
  }, [value]);

  // Auto-focus on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  // Refocus after send completes
  useEffect(() => {
    if (!disabled) {
      textareaRef.current?.focus();
    }
  }, [disabled]);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  }, [value, disabled, onSend]);

  return (
    <footer className="p-4 md:px-6 md:pb-8 bg-surface border-t border-outline-variant/30">
      <div className="max-w-[1000px] mx-auto relative">
        <div className="flex items-end gap-3 bg-surface-container-highest rounded-[28px] p-2 pr-3 shadow-sm border border-transparent focus-within:border-primary transition-all">
          <button
            className="p-3 text-on-surface-variant hover:text-primary transition-colors"
            tabIndex={0}
            aria-label="Attach file"
          >
            <span className="material-symbols-outlined">attach_file</span>
          </button>

          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            className="flex-1 bg-transparent border-none focus:ring-0 py-3 text-on-surface resize-none min-h-[48px] max-h-[200px]"
            style={{ fontSize: "16px", lineHeight: "24px", scrollbarWidth: "none" }}
            placeholder="Describe your startup or ask for grants, accelerators, competitions..."
            rows={1}
            disabled={disabled}
            aria-label="Chat message input"
          />

          <div className="flex items-center gap-1 mb-1">
            <button
              className="p-3 text-on-surface-variant hover:text-primary transition-colors"
              tabIndex={0}
              aria-label="Voice input"
            >
              <span className="material-symbols-outlined">mic</span>
            </button>
            <button
              onClick={handleSend}
              disabled={disabled || !value.trim()}
              className="w-12 h-12 bg-primary text-on-primary rounded-full flex items-center justify-center hover:opacity-90 active:scale-90 transition-transform disabled:opacity-50"
              tabIndex={0}
              aria-label="Send message"
            >
              <span className="material-symbols-outlined">send</span>
            </button>
          </div>
        </div>
      </div>
      <p
        className="text-center text-on-surface-variant mt-4"
        style={{ fontSize: "11px", fontWeight: 500, letterSpacing: "0.5px" }}
      >
        TRESTLE uses AI. Check for accuracy.
      </p>
    </footer>
  );
}
