"use client";

import { TrainSummary } from "@/lib/api";
import { Train, Clock, AlertTriangle, CheckCircle } from "lucide-react";
import Link from "next/link";

interface DelayBadgeProps {
  delayMin: number;
  status: string;
  size?: "sm" | "md";
}

export function DelayBadge({ delayMin, status, size = "md" }: DelayBadgeProps) {
  const cls = {
    on_time: "border-emerald-800/60 bg-emerald-950/50 text-emerald-400",
    delayed: "border-amber-800/60 bg-amber-950/50 text-amber-400",
    severely_delayed: "border-red-800/60 bg-red-950/50 text-red-400",
    unknown: "border-gray-700 bg-gray-900 text-gray-500",
  }[status] ?? "border-gray-700 bg-gray-900 text-gray-500";

  const Icon = {
    on_time: CheckCircle,
    delayed: Clock,
    severely_delayed: AlertTriangle,
    unknown: Clock,
  }[status] ?? Clock;

  const label =
    status === "on_time"
      ? "On Time"
      : status === "unknown"
      ? "No data"
      : `+${Math.round(delayMin)} min`;

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-medium ${cls} ${
        size === "sm" ? "text-[10px]" : "text-xs"
      }`}
    >
      <Icon className={size === "sm" ? "h-2.5 w-2.5" : "h-3 w-3"} />
      {label}
    </span>
  );
}

interface TrainCardProps {
  train: TrainSummary;
}

export function TrainCard({ train }: TrainCardProps) {
  return (
    <Link
      href={`/train/${train.train_number}`}
      className="glass glow-hover block rounded-xl p-4 transition"
      id={`train-card-${train.train_number}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-indigo-600/20">
            <Train className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="min-w-0">
            <div className="truncate font-semibold text-white">{train.name}</div>
            <div className="text-xs text-gray-500">
              {train.train_number} · {train.train_type ?? "Train"}
            </div>
          </div>
        </div>
        <DelayBadge delayMin={train.current_delay_min} status={train.status} />
      </div>

      <div className="mt-3 flex items-center gap-2 text-xs text-gray-500">
        <span className="truncate">{train.source_station}</span>
        <span className="flex-1 border-t border-dashed border-gray-700" />
        <span className="truncate">{train.destination_station}</span>
      </div>

      {train.next_station && (
        <div className="mt-2 text-[10px] text-gray-600">
          Next stop:{" "}
          <span className="text-indigo-400">{train.next_station}</span>
        </div>
      )}
    </Link>
  );
}
