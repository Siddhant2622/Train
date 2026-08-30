"use client";

import { useQuery } from "@tanstack/react-query";
import { trains as trainsApi } from "@/lib/api";
import { useTrainStream } from "@/hooks/useTrainStream";
import { EtaTable } from "@/components/EtaTable";
import { DelayBadge } from "@/components/TrainCard";
import { Train, Activity, Clock, ShieldAlert, Navigation } from "lucide-react";
import { use, useEffect, useState } from "react";
import { format, parseISO } from "date-fns";
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
    refetchInterval: 60_000,
  });

  // Connect to the train-specific WebSocket stream
  const { lastMessage, connected } = useTrainStream({ trainNumber: id });

  // Compute the current "live" view of the train
  const delayMin = lastMessage?.current_delay_min ?? trainData?.position?.current_delay_min ?? 0;
  const status = trainData?.position ? (delayMin <= 5 ? "on_time" : delayMin <= 30 ? "delayed" : "severely_delayed") : "unknown";
  
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
      <main className="page flex items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
      </main>
    );
  }

  if (isError || !trainData) {
    return (
      <main className="page container py-16 text-center">
        <ShieldAlert className="mx-auto mb-4 h-12 w-12 text-red-500/50" />
        <h1 className="text-xl font-bold text-white">Train Not Found</h1>
        <p className="mt-2 text-gray-400">Train {id} is not currently running or doesn't exist.</p>
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
              <div className="flex items-center gap-3 mb-2">
                <span className="flex items-center justify-center h-8 w-8 rounded-lg bg-indigo-600/20 text-indigo-400 font-bold">
                  {id}
                </span>
                <h1 className="text-2xl font-bold text-white tracking-tight">{trainData.name}</h1>
                <DelayBadge delayMin={delayMin} status={status} />
              </div>
              
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <span>{trainData.source_station}</span>
                <Navigation className="h-3 w-3 text-gray-600" />
                <span>{trainData.destination_station}</span>
                <span className="px-2 text-gray-700">|</span>
                <span>{trainData.total_distance_km} km</span>
              </div>
            </div>

            <div className="flex items-center gap-6">
              <div className="text-right">
                <div className="text-xs font-medium uppercase tracking-wider text-gray-500 mb-1">Live Speed</div>
                <div className="text-xl font-bold text-white tabular-nums">
                  {lastMessage?.speed_kmh != null ? Math.round(lastMessage.speed_kmh) : Math.round(trainData.position?.speed_kmh ?? 0)}
                  <span className="text-sm font-normal text-gray-500 ml-1">km/h</span>
                </div>
              </div>
              
              <div className="text-right">
                <div className="text-xs font-medium uppercase tracking-wider text-gray-500 mb-1">Model Layer</div>
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-indigo-950/40 border border-indigo-800/40 text-xs font-medium text-indigo-400">
                  <Activity className="h-3 w-3" />
                  {trainData.model_version === "xgboost_ensemble_v1" ? "XGBoost Ensemble" : "Physics Base"}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content - ETA Table */}
          <div className="lg:col-span-2">
            <div className="glass rounded-2xl p-1">
              <div className="flex items-center justify-between p-5 border-b border-white/5">
                <h2 className="font-semibold text-white flex items-center gap-2">
                  <Clock className="h-4 w-4 text-indigo-400" />
                  Live ETAs
                </h2>
                <div className="flex items-center gap-2 text-xs">
                  {connected ? (
                    <span className="inline-flex items-center gap-1.5 text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded border border-emerald-400/20">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      Live Feed Active
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 text-amber-400 bg-amber-400/10 px-2 py-1 rounded border border-amber-400/20">
                      <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                      Reconnecting...
                    </span>
                  )}
                </div>
              </div>
              
              <div className="p-2">
                <EtaTable stops={upcomingStops} />
              </div>
            </div>
          </div>

          {/* Sidebar - Mini Map */}
          <div>
            <div className="glass rounded-2xl p-1 h-[400px] lg:h-full min-h-[400px] flex flex-col">
              <div className="p-5 border-b border-white/5 flex-shrink-0">
                <h2 className="font-semibold text-white">Current Location</h2>
                <div className="mt-1 text-xs text-gray-400 flex items-center gap-2">
                  Between <strong className="text-white">{lastMessage?.last_station ?? trainData.position?.last_station}</strong> and <strong className="text-white">{lastMessage?.next_station ?? trainData.position?.next_station}</strong>
                </div>
              </div>
              <div className="flex-1 relative rounded-b-xl overflow-hidden">
                {/* 
                  To show the train on a map, we re-use LiveMap but just pass the single train.
                  We need to convert the train detail shape back to the summary shape expected by LiveMap.
                */}
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
