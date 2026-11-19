import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Cpu,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { Verdict } from "@/types/problems";

const verdictConfig: Record<
  Verdict,
  {
    label: string;
    variant: "emerald" | "rose" | "amber" | "neutral";
  }
> = {
  accepted: { label: "Accepted", variant: "emerald" },
  wrong_answer: { label: "Wrong Answer", variant: "rose" },
  compilation_error: { label: "Compilation Error", variant: "amber" },
  runtime_error: { label: "Runtime Error", variant: "rose" },
  time_limit_exceeded: { label: "Time Limit Exceeded", variant: "amber" },
  memory_limit_exceeded: { label: "Memory Limit Exceeded", variant: "amber" },
  internal_error: { label: "Engine Error", variant: "neutral" },
  pending: { label: "Pending", variant: "neutral" },
};

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  const cfg = verdictConfig[verdict];
  const Icon =
    verdict === "accepted"
      ? CheckCircle2
      : verdict === "time_limit_exceeded"
        ? Clock
        : verdict === "memory_limit_exceeded"
          ? Cpu
          : verdict === "wrong_answer" || verdict === "runtime_error"
            ? XCircle
            : AlertTriangle;

  return (
    <Badge variant={cfg.variant}>
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      <span>{cfg.label}</span>
    </Badge>
  );
}
