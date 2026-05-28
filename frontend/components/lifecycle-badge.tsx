import type { GrantLifecycleStatus } from "@/lib/domain/lifecycle";
import { GRANT_LIFECYCLE_LABELS } from "@/lib/domain/lifecycle";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const tone: Record<GrantLifecycleStatus, string> = {
  saved: "border-outline bg-surface-container text-on-surface",
  applied: "border-primary/40 bg-primary-fixed text-on-primary-fixed",
  under_review: "border-secondary bg-secondary-container text-on-secondary-container",
  awarded: "border-primary bg-primary-container text-on-primary-container",
  rejected: "border-error/40 bg-error-container text-on-error-container",
};

export function LifecycleBadge({
  status,
  className,
}: {
  status: GrantLifecycleStatus;
  className?: string;
}) {
  return (
    <Badge
      variant="outline"
      className={cn("rounded-full font-medium", tone[status], className)}
    >
      {GRANT_LIFECYCLE_LABELS[status]}
    </Badge>
  );
}
