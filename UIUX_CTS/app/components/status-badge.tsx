import { cn } from "@/lib/utils";
import type { PatientStatus } from "@/lib/mock-data";

const styles: Record<PatientStatus, string> = {
  "Needs review": "border-primary/25 bg-primary/10 text-primary",
  "Outreach sent": "border-border bg-muted text-foreground",
  Scheduled: "border-border bg-muted text-muted-foreground",
  Closed: "border-border bg-transparent text-muted-foreground",
};

export function StatusBadge({ status }: { status: PatientStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center whitespace-nowrap rounded-full border px-2.5 py-1 text-xs",
        styles[status],
      )}
    >
      {status}
    </span>
  );
}
