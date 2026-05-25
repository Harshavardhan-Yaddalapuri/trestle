"use client";

import { Button } from "@/components/ui/button";

interface ActionButtonsProps {
  saved: boolean;
  onSave: () => void;
  onDismiss: () => void;
  onTrack: () => void;
  onInterested?: () => void;
}

export default function ActionButtons({
  saved,
  onSave,
  onDismiss,
  onTrack,
  onInterested,
}: ActionButtonsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <Button
        variant={saved ? "default" : "outline"}
        size="sm"
        className="rounded-full gap-1.5"
        onClick={onSave}
      >
        <span className="material-symbols-outlined" style={{ fontSize: "14px" }}>
          {saved ? "bookmark" : "bookmark_border"}
        </span>
        {saved ? "Saved" : "Save"}
      </Button>
      <Button variant="outline" size="sm" className="rounded-full gap-1.5" onClick={onDismiss}>
        <span className="material-symbols-outlined" style={{ fontSize: "14px" }}>close</span>
        Dismiss
      </Button>
      <Button variant="outline" size="sm" className="rounded-full gap-1.5" onClick={onTrack}>
        <span className="material-symbols-outlined" style={{ fontSize: "14px" }}>notifications</span>
        Track
      </Button>
      {onInterested && (
        <Button size="sm" className="rounded-full gap-1.5" onClick={onInterested}>
          <span className="material-symbols-outlined" style={{ fontSize: "14px" }}>favorite</span>
          I&apos;m interested
        </Button>
      )}
    </div>
  );
}
