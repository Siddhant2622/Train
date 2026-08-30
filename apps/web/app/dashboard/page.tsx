"use client";

import { useQuery } from "@tanstack/react-query";
import { trains as trainsApi, admin, FleetSummary, TrainSummary } from "@/lib/api";
import { FleetKpis } from "@/components/FleetKpis";
import { TrainCard } from "@/components/TrainCard";
import { DelayBadge } from "@/components/TrainCard";
import { RefreshCw, AlertTriangle, Train } from "lucide-react";
import Link from "next/link";
import { format, parseISO } from "date-fns";

export default function DashboardPage() {
  const {
    data: fleet,
    isLoading: fleetLoading,
    refetch: refetchFleet,
    dataUpdatedAt,
  } = useQuery({
    queryKey: ["fleet-summary"],
    queryFn: admin.fleetSummary,
    refetchInterval: 30_000,
    retry: false,
  });

  const { data: trainsList, isLoading: trainsLoading } = useQuery({
    queryKey: ["trains-list"],
    queryFn: () => trainsApi.list({ page_size: 50 }),
    refetchInterval: 30_000,
    retry: false,
  });

  const delayed = trainsList?.trains
    ?.filter((t) => t.status !== "on_time" && t.status !== "unknown")
    ?.sort((a, b) => b.current_delay_min - a.current_delay_min) ?? [];

  return (
    <main className="page">
      <div className="container py-8">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Control Room</h1>
            <p className="text-sm text-gray-500">
              Live fleet overview — refreshes every 30s
              {dataUpdatedAt
                ? ` · Last update: ${format(new Date(dataUpdatedAt), "HH:mm:ss")}`
                : ""}
            </p>
          </div>
          <button
            onClick={() => refetchFleet()}
            className="btn-ghost text-xs"
            id="dashboard-refresh-btn"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </button>
        </div>

        {/* KPI strip */}
        <FleetKpis data={fleet ?? null} loading={fleetLoading} />

        {/* No data state */}
        {!fleetLoading && (!fleet || fleet.total_active === 0) && (
          <div className="mt-4 glass rounded-xl p-6 text-center">
            <Train className="mx-auto mb-2 h-8 w-8 text-gray-700" />
            <p className="text-sm text-gray-500">
              No active trains today. Start the simulator:{" "}
              <code className="text-xs text-indigo-400">docker compose up simulator</code>
            </p>
          </div>
        )}

        <div className="mt-8 grid gap-6 lg:grid-cols-3">
          {/* Delayed trains table */}
          <div className="lg:col-span-2">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold text-white">
                Delayed Trains
                {delayed.length > 0 && (
                  <span className="ml-2 rounded-full bg-amber-950/50 px-2 py-0.5 text-xs text-amber-400">
                    {delayed.length}
                  </span>
                )}
              </h2>
              <span className="text-xs text-gray-600">Click row to view ETA</span>
            </div>
            <div className="glass overflow-hidden rounded-xl">
              {trainsLoading ? (
                <div className="p-6">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="mb-3 h-12 skeleton rounded-lg" />
                  ))}
                </div>
              ) : delayed.length === 0 ? (
                <div className="py-12 text-center text-sm text-gray-600">
                  All trains running on time ✓
                </div>
              ) : (
                <table className="arrivals-table">
                  <thead>
                    <tr>
                      <th>Train</th>
                      <th>Route</th>
                      <th>Next Stop</th>
                      <th>Delay</th>
                    </tr>
                  </thead>
                  <tbody>
                    {delayed.map((t) => (
                      <tr
                        key={t.train_number}
                        className="cursor-pointer"
                        onClick={() => (window.location.href = `/train/${t.train_number}`)}
                        id={`delayed-row-${t.train_number}`}
                      >
                        <td>
                          <div className="font-medium text-white">{t.name}</div>
                          <div className="text-xs text-gray-600">{t.train_number}</div>
                        </td>
                        <td className="text-xs text-gray-500">
                          {t.source_station} → {t.destination_station}
                        </td>
                        <td className="text-xs text-gray-400">
                          {t.next_station ?? "—"}
                        </td>
                        <td>
                          <DelayBadge delayMin={t.current_delay_min} status={t.status} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          {/* On-time sidebar */}
          <div>
            <h2 className="mb-3 font-semibold text-white">All Active Trains</h2>
            <div className="flex max-h-[520px] flex-col gap-2 overflow-y-auto pr-1">
              {trainsLoading
                ? Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="h-20 skeleton rounded-xl" />
                  ))
                : (trainsList?.trains ?? []).map((t) => (
                    <TrainCard key={t.train_number} train={t} />
                  ))}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
