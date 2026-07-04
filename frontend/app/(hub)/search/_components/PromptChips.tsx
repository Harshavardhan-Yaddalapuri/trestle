"use client";

interface PromptChipsProps {
  prompts: string[];
  onSelect: (prompt: string) => void;
}

export default function PromptChips({ prompts, onSelect }: PromptChipsProps) {
  return (
    <div className="flex flex-wrap gap-2 mt-2">
      {prompts.map((prompt) => (
        <button
          key={prompt}
          onClick={() => onSelect(prompt)}
          className="bg-secondary-container/60 text-on-secondary-container px-4 py-2 rounded-full hover:bg-secondary-container transition-colors"
          style={{ fontSize: "14px", fontWeight: 500 }}
        >
          {prompt}
        </button>
      ))}
    </div>
  );
}
