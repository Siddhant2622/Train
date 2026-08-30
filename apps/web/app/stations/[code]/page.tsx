"use client";

import { useQuery } from "@tanstack/react-query";
import { stations as stationsApi } from "@/lib/api";
import { use } from "react";
import { ShieldAlert, MapPin, Clock } from "lucide-react";
import { format, parseISO } from "date-fns";
import { DelayBadge } from "@/components/TrainCard";

export default function StationArrivalsPage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = use(params);

  // Fetch station details
  const {
    data: station,
    isLoading: stationLoading,
    isError: stationError,
  } = useQuery({
    queryKey: ["station", code],
    queryFn: () => stationsApi.get(code),
    retry: false,
  });

  // Fetch upcoming arrivals
  const {
    data: arrivalsData,
    isLoading: arrivalsLoading,
    refetch,
    dataUpdatedAt,
  } = useQuery({
    queryKey: ["station-arrivals", code],
    queryFn: () => stationsApi.arrivals(code, 30),
    refetchInterval: 30_000,
    enabled: !!station,
  });

  if (stationLoading) {
    return (
      <main className="page flex items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
      </main>
    );
  }

  if (stationError || !station) {
    return (
      <main className="page container py-16 text-center">
        <ShieldAlert className="mx-auto mb-4 h-12 w-12 text-red-500/50" />
        <h1 className="text-xl font-bold text-white">Station Not Found</h1>
        <p className="mt-2 text-gray-400">Could not find station with code {code.toUpperCase()}.</p>
      </main>
    );
  }

  return (
    <main className="page">
      <div className="container py-8 max-w-5xl">
        {/* Header */}
        <div className="glass rounded-2xl p-6 lg:p-8 mb-8 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl -mt-20 -mr-20" />
          
          <div className="relative z-10 flex flex-col sm:flex-row sm:items-end justify-between gap-6">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <span className="flex items-center justify-center h-10 w-10 rounded-xl bg-emerald-600/20 text-emerald-400 font-bold text-lg">
                  {station.station_code}
                </span>
                <h1 className="text-3xl font-bold text-white tracking-tight">{station.name}</h1>
              </div>
              <div className="flex items-center gap-2 text-gray-400">
                <MapPin className="h-4 w-4" />
                <span>{station.city}, {station.state}</span>
                {station.zone && (
                  <>
                    <span className="px-2 text-gray-700">•</span>
                    <span>Zone: {station.zone}</span>
                  </>
                )}
                <span className="px-2 text-gray-700">•</span>
                <span>Platforms: {station.platform_count ?? "Unknown"}</span>
              </div>
            </div>
            
            <div className="text-right">
              <div className="text-xs text-gray-500 mb-1">Upcoming Arrivals</div>
              <div className="text-2xl font-bold text-white tabular-nums">
                {arrivalsData?.arrivals.length ?? 0}
              </div>
            </div>
          </div>
        </div>

        {/* Board */}
        <div className="glass rounded-2xl p-1 overflow-hidden">
          <div className="flex items-center justify-between p-5 border-b border-white/5">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <Clock className="h-4 w-4 text-emerald-400" />
              Arrivals Board
            </h2>
            <div className="text-xs text-gray-500">
              {dataUpdatedAt ? `Last updated: ${format(new Date(dataUpdatedAt), "HH:mm:ss")}` : "Loading..."}
            </div>
          </div>

          <div className="p-2 overflow-x-auto">
            {arrivalsLoading ? (
              <div className="p-4 space-y-3">
                {Array.from({ length: 10 }).map((_, i) => (
                  <div key={i} className="h-12 skeleton rounded-lg" />
                ))}
              </div>
            ) : arrivalsData?.arrivals.length === 0 ? (
              <div className="py-16 text-center text-gray-500">
                No upcoming arrivals in the next few hours.
              </div>
            ) : (
              <table className="arrivals-table whitespace-nowrap">
                <thead>
                  <tr>
                    <th>Train</th>
                    <th>Origin</th>
                    <th>Destination</th>
                    <th className="text-right">Scheduled</th>
                    <th className="text-right">Predicted ETA</th>
                    <th className="text-right">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {arrivalsData?.arrivals.map((arr) => (
                    <tr 
                      key={`${arr.train_number}-${arr.scheduled_arrival}`}
                      className="cursor-pointer group"
                      onClick={() => (window.location.href = `/train/${arr.train_number}`)}
                    >
                      <td className="py-3">
                        <div className="font-semibold text-white group-hover:text-indigo-400 transition-colors">
                          {arr.train_name}
                        </div>
                        <div className="text-xs text-gray-500">
                          {arr.train_number} • {arr.train_type ?? "Train"}
                        </div>
                      </td>
                      <td className="py-3 text-gray-400">{arr.source_station}</td>
                      <td className="py-3 text-gray-400">{arr.destination_station}</td>
                      <td className="py-3 text-right tabular-nums text-gray-500">
                        {arr.scheduled_arrival ? format(parseISO(arr.scheduled_arrival), "HH:mm") : "—"}
                      </td>
                      <td className="py-3 text-right">
                        <span className="tabular-nums font-bold text-white text-lg">
                          {arr.predicted_eta ? format(parseISO(arr.predicted_eta), "HH:mm") : "—"}
                        </span>
                      </td>
                      <td className="py-3 text-right">
                        <DelayBadge delayMin={arr.delay_min} status={arr.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
