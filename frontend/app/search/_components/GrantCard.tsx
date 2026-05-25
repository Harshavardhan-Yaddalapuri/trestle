"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import ActionButtons from "./ActionButtons";

export interface GrantData {
  name: string;
  amount: string;
  deadline: string;
  daysLeft?: number;
  eligibility: string;
  sourceUrl: string;
  freshness: "Verified this week" | "Verified recently" | "Needs verification";
  description?: string;
  budgetInfo?: string;
  eligibilityCriteria?: string[];
}

function FreshnessBadge({ freshness }: { freshness: GrantData["freshness"] }) {
  const color =
    freshness === "Verified this week"
      ? "bg-primary/10 text-primary"
      : freshness === "Verified recently"
      ? "bg-secondary-container text-on-secondary-container"
      : "bg-error-container text-on-error-container";

  return (
    <span className={`px-2 py-0.5 rounded-full ${color}`} style={{ fontSize: "11px", fontWeight: 500 }}>
      {freshness}
    </span>
  );
}

function DeadlineTag({ deadline, daysLeft }: { deadline: string; daysLeft?: number }) {
  const urgent = daysLeft !== undefined && daysLeft <= 14;
  return (
    <div className="flex items-center gap-1.5">
      <span className={`material-symbols-outlined ${urgent ? "text-error" : "text-on-surface-variant"}`} style={{ fontSize: "14px" }}>
        schedule
      </span>
      <span className={urgent ? "text-error" : "text-on-surface-variant"} style={{ fontSize: "11px", fontWeight: 500 }}>
        {deadline}
        {daysLeft !== undefined && ` (${daysLeft}d left)`}
      </span>
    </div>
  );
}

export default function GrantCard({ grant }: { grant: GrantData }) {
  const [saved, setSaved] = useState(false);

  return (
    <div className="bg-surface-container rounded-2xl p-4 hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex justify-between items-start mb-2">
        <div className="flex-1">
          <p
            className="font-[family-name:var(--font-plus-jakarta)] text-on-surface leading-tight"
            style={{ fontSize: "18px", lineHeight: "24px", fontWeight: 600 }}
          >
            {grant.name}
          </p>
          <p className="text-primary font-bold mt-1" style={{ fontSize: "16px" }}>
            {grant.amount}
          </p>
        </div>
        <FreshnessBadge freshness={grant.freshness} />
      </div>

      {/* Deadline */}
      <div className="mb-3">
        <DeadlineTag deadline={grant.deadline} daysLeft={grant.daysLeft} />
      </div>

      {/* Eligibility rationale */}
      <p className="text-on-surface-variant mb-3" style={{ fontSize: "14px", lineHeight: "20px" }}>
        {grant.eligibility}
      </p>

      {/* Source URL */}
      <a
        href={grant.sourceUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 text-primary hover:underline mb-3"
        style={{ fontSize: "13px", fontWeight: 500 }}
      >
        <span className="material-symbols-outlined" style={{ fontSize: "14px" }}>open_in_new</span>
        View source
      </a>

      {/* Action buttons */}
      <ActionButtons
        saved={saved}
        onSave={() => setSaved(!saved)}
        onDismiss={() => {}}
        onTrack={() => {}}
      />

      {/* Deep dive trigger */}
      <Dialog>
        <DialogTrigger asChild>
          <Button variant="outline" className="w-full mt-3 rounded-xl">
            <span className="material-symbols-outlined" style={{ fontSize: "16px" }}>expand_content</span>
            Full details
          </Button>
        </DialogTrigger>
        <DialogContent className="max-w-lg bg-surface-container-lowest rounded-3xl border-outline-variant">
          <DialogHeader>
            <DialogTitle className="font-[family-name:var(--font-plus-jakarta)] text-on-surface" style={{ fontSize: "22px", lineHeight: "28px", fontWeight: 500 }}>
              {grant.name}
            </DialogTitle>
          </DialogHeader>

          <div className="flex flex-col gap-4 mt-2">
            {/* Amount + Deadline + Freshness */}
            <div className="flex flex-wrap items-center gap-3">
              <Badge className="bg-primary text-on-primary rounded-full">{grant.amount}</Badge>
              <DeadlineTag deadline={grant.deadline} daysLeft={grant.daysLeft} />
              <FreshnessBadge freshness={grant.freshness} />
            </div>

            <Separator />

            {/* Description */}
            {grant.description && (
              <div>
                <p className="text-on-surface font-bold mb-1" style={{ fontSize: "14px" }}>Description</p>
                <p className="text-on-surface-variant" style={{ fontSize: "14px", lineHeight: "20px" }}>
                  {grant.description}
                </p>
              </div>
            )}

            {/* Eligibility criteria */}
            <div>
              <p className="text-on-surface font-bold mb-1" style={{ fontSize: "14px" }}>Eligibility</p>
              {grant.eligibilityCriteria && grant.eligibilityCriteria.length > 0 ? (
                <ul className="flex flex-col gap-1.5">
                  {grant.eligibilityCriteria.map((c) => (
                    <li key={c} className="flex items-start gap-2 text-on-surface-variant" style={{ fontSize: "14px", lineHeight: "20px" }}>
                      <span className="material-symbols-outlined text-primary mt-0.5" style={{ fontSize: "14px" }}>check_circle</span>
                      {c}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-on-surface-variant" style={{ fontSize: "14px" }}>{grant.eligibility}</p>
              )}
            </div>

            {/* Budget info */}
            {grant.budgetInfo && (
              <div>
                <p className="text-on-surface font-bold mb-1" style={{ fontSize: "14px" }}>Budget &amp; Funding</p>
                <p className="text-on-surface-variant" style={{ fontSize: "14px", lineHeight: "20px" }}>
                  {grant.budgetInfo}
                </p>
              </div>
            )}

            <Separator />

            {/* Source link */}
            <a
              href={grant.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-primary hover:underline"
              style={{ fontSize: "14px", fontWeight: 500 }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: "16px" }}>open_in_new</span>
              View original source
            </a>

            {/* Actions */}
            <div className="flex gap-2">
              <Button className="flex-1 rounded-full gap-2">
                <span className="material-symbols-outlined" style={{ fontSize: "16px" }}>favorite</span>
                I&apos;m interested
              </Button>
              <Button variant="outline" className="flex-1 rounded-full gap-2">
                <span className="material-symbols-outlined" style={{ fontSize: "16px" }}>bookmark</span>
                {saved ? "Saved" : "Save"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
