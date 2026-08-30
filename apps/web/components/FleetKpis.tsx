"use client";

import { FleetSummary } from "@/lib/api";
import { Activity, AlertTriangle, CheckCircle, Clock, TrendingDown } from "lucide-react";

interface FleetKpisProps {
  data: FleetSummary | null;
  loading?: boolean;
}

function KpiCard({
  label,
  value,
  sub,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  accent: string;
}) {
  return (
    <div className="glass rounded-xl p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</p>
          <p className={`mt-1 text-2xl font-bold ${accent}`}>{value}</p>
          {sub && <p className="mt-0.5 text-xs text-gray-600">{sub}</p>}
        </div>
        <div className={`rounded-lg p-2 ${accent.replace("text-", "bg-").replace("400", "950/60")}`}>
          <Icon className={`h-4 w-4 ${accent}`} />
        </div>
      </div>
    </div>
  );
}

export function FleetKpis({ data, loading }: FleetKpisProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="glass h-24 animate-pulse rounded-xl" />
        ))}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="glass rounded-xl p-6 text-center text-sm text-gray-500">
        Fleet data unavailable — start the simulator to see live KPIs.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <KpiCard
        label="Active Trains"
        value={data.total_active}
        sub="Running today"
        icon={Activity}
        accent="text-indigo-400"
      />
      <KpiCard
        label="On Time"
        value={`${data.on_time_percentage}%`}
        sub={`${data.on_time} trains`}
        icon={CheckCircle}
        accent="text-emerald-400"
      />
      <KpiCard
        label="Delayed"
        value={data.delayed}
        sub={`Avg +${data.avg_delay_min} min`}
        icon={Clock}
        accent="text-amber-400"
      />
      <KpiCard
        label="Severe"
        value={data.severely_delayed}
        sub={`Max +${data.max_delay_min} min`}
        icon={AlertTriangle}
        accent="text-red-400"
      />
    </div>
  );
}
