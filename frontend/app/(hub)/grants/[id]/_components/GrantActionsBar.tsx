"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

export default function GrantActionsBar({ grantName }: { grantName: string }) {
  const [msg, setMsg] = useState<string | null>(null);

  function demo(label: string) {
    setMsg(`${label} — demo only until the API is wired. (${grantName})`);
    window.setTimeout(() => setMsg(null), 4000);
  }

  return (
    <div className="space-y-3">
      {msg && (
        <p className="text-sm rounded-lg bg-primary-container text-on-primary-container px-3 py-2" role="status">
          {msg}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button type="button" onClick={() => demo("Open application portal")}>
          Open application
        </Button>
        <Button type="button" variant="secondary" onClick={() => demo("Marked as submitted")}>
          Mark submitted
        </Button>
        <Button type="button" variant="outline" onClick={() => demo("Snoozed reminder")}>
          Snooze 1 week
        </Button>
      </div>
    </div>
  );
}
