"use client";

import { useQuery } from "@tanstack/react-query";
import { trains as trainsApi } from "@/lib/api";
import { useTrainStream } from "@/hooks/useTrainStream";
import { TrainTimeline } from "@/components/TrainTimeline";
import { DelayBadge } from "@/components/TrainCard";
import { Train, Activity, Clock, ShieldAlert, Navigation, Layers, CheckCircle2 } from "lucide-react";
import { use } from "react";
import dynamic from "next/dynamic";

const LiveMap = dynamic(() => import("@/components/LiveMap"), { ssr: false });

export default function TrainDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  // Fetch initial data (static until re-fetched or WS updates)
  const {
    data: trainData,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["train-detail", id],
    queryFn: () => trainsApi.get(id),
    refetchInterval: 30_000,
  });

  // Connect to the train-specific WebSocket stream
  const { lastMessage, connected } = useTrainStream({ trainNumber: id });

  // Compute the current "live" view of the train
  const delayMin = lastMessage?.current_delay_min ?? trainData?.position?.current_delay_min ?? 0;
  const status = trainData?.position ? (delayMin <= 5 ? "on_time" : delayMin <= 30 ? "delayed" : "severely_delayed") : "unknown";
  const rawSpeed = lastMessage?.speed_kmh != null ? lastMessage.speed_kmh : trainData?.position?.speed_kmh;
  const currentSpeed = rawSpeed != null ? Math.max(0, rawSpeed) : null;
  const isMoving = currentSpeed != null && currentSpeed > 2.0;

  // Merge live ETA updates with the schedule
  const upcomingStops = trainData?.upcoming_stops.map(stop => {
    // If the WS sent an update for this stop, merge it
    const liveUpdate = lastMessage?.upcoming_stops?.find(s => s.station_code === stop.station_code);
    if (liveUpdate) {
      return {
        ...stop,
        predicted_eta: liveUpdate.predicted_eta,
        lower_bound: liveUpdate.lower_bound,
        upper_bound: liveUpdate.upper_bound,
        delay_min: liveUpdate.delay_min,
      };
    }
    return stop;
  }) ?? [];

  if (isLoading) {
    return (
      <main className="page flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
          <p className="text-xs text-gray-400 font-medium tracking-wide uppercase">Connecting to live feed...</p>
        </div>
      </main>
    );
  }

  if (isError || !trainData) {
    return (
      <main className="page container py-16 text-center">
        <ShieldAlert className="mx-auto mb-4 h-12 w-12 text-red-500/50" />
        <h1 className="text-xl font-bold text-white">Train Not Found</h1>
        <p className="mt-2 text-gray-400">Train {id} is not currently running or telemetry is unreachable.</p>
      </main>
    );
  }

  return (
    <main className="page">
      <div className="container py-8">
        {/* Header Section */}
        <div className="glass rounded-2xl p-6 lg:p-8 relative overflow-hidden">
          {/* Background decoration */}
          <div className="absolute top-0 right-0 -mt-20 -mr-20 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl" />
          
          <div className="relative z-10 flex flex-col md:flex-row md:items-start justify-between gap-6">
            <div>
              <div className="flex items-center gap-3 mb-2 flex-wrap">
                <span className="flex items-center justify-center h-8 px-3 rounded-lg bg-indigo-600/25 text-indigo-300 font-mono font-bold text-sm border border-indigo-500/30">
                  {id}
                </span>
                <h1 className="text-2xl lg:text-3xl font-bold text-white tracking-tight">{trainData.name}</h1>
                <DelayBadge delayMin={delayMin} status={status} />
              </div>
              
              <div className="flex items-center gap-2 text-sm text-gray-300 flex-wrap mt-2">
                <span className="font-semibold text-white">{trainData.source_station}</span>
                <Navigation className="h-3 w-3 text-indigo-400" />
                <span className="font-semibold text-white">{trainData.destination_station}</span>
                <span className="px-2 text-gray-600">|</span>
                <span>{trainData.total_distance_km ? `${trainData.total_distance_km} km` : "Express Route"}</span>
                {trainData.total_halts && (
                  <>
                    <span className="px-2 text-gray-600">|</span>
                    <span>{trainData.total_halts} Scheduled Halts</span>
                  </>
                )}
                {trainData.train_type && (
                  <>
                    <span className="px-2 text-gray-600">|</span>
                    <span className="text-indigo-400 font-medium">{trainData.train_type}</span>
                  </>
                )}
              </div>

              {/* Coach Composition */}
              {trainData.coach_position && (
                <div className="mt-3 flex items-center gap-2 flex-wrap text-xs text-gray-400">
                  <span className="inline-flex items-center gap-1 font-semibold text-gray-300">
                    <Layers className="h-3 w-3 text-indigo-400" />
                    Formation:
                  </span>
                  <span className="font-mono text-[11px] bg-white/5 px-2 py-0.5 rounded border border-white/5 text-gray-300">
                    {trainData.coach_position}
                  </span>
                </div>
              )}
            </div>

            <div className="flex items-center gap-4 flex-wrap">
              {/* Live Speed Widget */}
              <div className="glass px-4 py-2.5 rounded-xl border border-white/5 text-right min-w-[135px]">
                <div className="text-[11px] font-medium uppercase tracking-wider text-gray-400 mb-0.5 flex items-center justify-end gap-1.5">
                  <span className={`h-2 w-2 rounded-full ${isMoving ? "bg-emerald-400 animate-pulse" : "bg-amber-400"}`} />
                  {isMoving ? "Live Speed" : "At Station"}
                </div>
                <div className="text-2xl font-bold text-white tabular-nums flex items-baseline justify-end">
                  {currentSpeed != null ? Math.round(currentSpeed) : "—"}
                  <span className="text-xs font-normal text-gray-400 ml-1">km/h</span>
                </div>
                <div className="text-[10px] text-gray-400 mt-0.5">
                  {isMoving ? "Cruising in transit" : "Stationary / Halting"}
                </div>
              </div>
              
              <div className="text-right">
                <div className="text-xs font-medium uppercase tracking-wider text-gray-400 mb-1">Data Source</div>
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-indigo-950/50 border border-indigo-800/50 text-xs font-medium text-indigo-300">
                  <Activity className="h-3 w-3 text-emerald-400" />
                  {trainData.model_version === "railradar_live_v1" ? "RailRadar Live Telemetry" : "Physics + Kalman"}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content - Timeline & Halts */}
          <div className="lg:col-span-2">
            <div className="glass rounded-2xl p-1">
              <div className="flex items-center justify-between p-5 border-b border-white/5">
                <h2 className="font-semibold text-white flex items-center gap-2">
                  <Clock className="h-4 w-4 text-indigo-400" />
                  Live Station Halts & ETAs
                </h2>
                <div className="flex items-center gap-2 text-xs">
                  {connected ? (
                    <span className="inline-flex items-center gap-1.5 text-emerald-400 bg-emerald-400/10 px-2.5 py-1 rounded-md border border-emerald-400/20 font-medium">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      Live Feed Connected
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 text-emerald-400 bg-emerald-400/10 px-2.5 py-1 rounded-md border border-emerald-400/20 font-medium">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      Live Telemetry Active
                    </span>
                  )}
                </div>
              </div>
              
              <div className="p-2">
                <TrainTimeline 
                  stops={upcomingStops} 
                  livePosition={
                    lastMessage 
                      ? {
                          latitude: lastMessage.latitude,
                          longitude: lastMessage.longitude,
                          speed_kmh: lastMessage.speed_kmh,
                          last_station: lastMessage.last_station,
                          next_station: lastMessage.next_station,
                          distance_to_next_km: lastMessage.distance_to_next_km ?? trainData.position?.distance_to_next_km ?? null,
                          current_delay_min: lastMessage.current_delay_min,
                          updated_at: lastMessage.timestamp,
                          source: "websocket"
                        }
                      : trainData.position
                  } 
                />
              </div>
            </div>
          </div>

          {/* Sidebar - Mini Map */}
          <div>
            <div className="glass rounded-2xl p-1 h-[420px] lg:h-full min-h-[420px] flex flex-col">
              <div className="p-5 border-b border-white/5 flex-shrink-0">
                <h2 className="font-semibold text-white">Current Track Position</h2>
                <div className="mt-1 text-xs text-gray-400 flex items-center gap-2">
                  Between <strong className="text-white">{lastMessage?.last_station ?? trainData.position?.last_station ?? "Origin"}</strong> and <strong className="text-white">{lastMessage?.next_station ?? trainData.position?.next_station ?? "Terminus"}</strong>
                </div>
              </div>
              <div className="flex-1 relative rounded-b-xl overflow-hidden">
                <LiveMap 
                  trains={[{
                    train_number: trainData.train_number,
                    name: trainData.name,
                    train_type: trainData.train_type,
                    source_station: trainData.source_station,
                    destination_station: trainData.destination_station,
                    current_delay_min: delayMin,
                    status: status,
                    latitude: lastMessage?.latitude ?? trainData.position?.latitude ?? 0,
                    longitude: lastMessage?.longitude ?? trainData.position?.longitude ?? 0,
                    speed_kmh: currentSpeed,
                    next_station: lastMessage?.next_station ?? trainData.position?.next_station ?? null,
                    last_updated: lastMessage?.timestamp ?? trainData.position?.updated_at ?? null,
                  }]} 
                  onTrainSelect={() => {}} 
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
