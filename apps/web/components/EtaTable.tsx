"use client";

import { StopEta } from "@/lib/api";
import { format, parseISO } from "date-fns";

interface EtaTableProps {
  stops: StopEta[];
  compact?: boolean;
}

function fmtTime(iso: string | null | undefined) {
  if (!iso) return "—";
  try {
    return format(parseISO(iso), "HH:mm");
  } catch {
    return "—";
  }
}

function fmtDelay(min: number) {
  if (min <= 0) return <span className="text-emerald-400">On time</span>;
  if (min <= 30) return <span className="text-amber-400">+{Math.round(min)} min</span>;
  return <span className="text-red-400">+{Math.round(min)} min</span>;
}

export function EtaTable({ stops, compact = false }: EtaTableProps) {
  if (!stops.length) {
    return (
      <div className="py-8 text-center text-sm text-gray-600">
        No upcoming stops — train may have reached its destination.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/5">
            <th className="pb-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              Station
            </th>
            <th className="pb-2 text-right text-xs font-medium uppercase tracking-wide text-gray-500">
              Scheduled
            </th>
            <th className="pb-2 text-right text-xs font-medium uppercase tracking-wide text-gray-500">
              Predicted ETA
            </th>
            {!compact && (
              <th className="pb-2 text-right text-xs font-medium uppercase tracking-wide text-gray-500">
                Delay
              </th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {stops.map((stop) => (
            <tr key={stop.station_code} className="group">
              <td className="py-2.5 pr-4">
                <div className="font-medium text-white">{stop.station_name}</div>
                <div className="text-[10px] text-gray-600">{stop.station_code}</div>
              </td>
              <td className="py-2.5 text-right tabular-nums text-gray-500">
                {fmtTime(stop.scheduled_arrival)}
              </td>
              <td className="py-2.5 text-right">
                <div className="tabular-nums font-semibold text-white">
                  {fmtTime(stop.predicted_eta)}
                </div>
                {!compact && (
                  <div className="text-[10px] text-gray-600">
                    ±{Math.round((parseISO(stop.upper_bound).getTime() - parseISO(stop.lower_bound).getTime()) / 120000)} min
                  </div>
                )}
                {!compact && stop.explanation?.shap_factors && (
                  <div className="mt-1 flex flex-col items-end gap-0.5">
                    {stop.explanation.shap_factors.map((factor: string, idx: number) => (
                      <span key={idx} className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-indigo-950/40 text-indigo-400/80 border border-indigo-800/20">
                        {factor}
                      </span>
                    ))}
                  </div>
                )}
              </td>
              {!compact && (
                <td className="py-2.5 text-right tabular-nums text-sm">
                  {fmtDelay(stop.delay_min)}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
