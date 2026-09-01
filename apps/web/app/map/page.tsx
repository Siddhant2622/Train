"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { trains as trainsApi, TrainSummary } from "@/lib/api";
import { useTrainStream, TrainStreamMessage } from "@/hooks/useTrainStream";
import { X, Train, Clock, ArrowRight, ExternalLink } from "lucide-react";
import Link from "next/link";
import { DelayBadge } from "@/components/TrainCard";

// MapLibre must be dynamically imported (no SSR — it uses window)
const LiveMap = dynamic(() => import("@/components/LiveMap"), { ssr: false });

interface SelectedTrain {
  summary: TrainSummary;
  liveMsg?: TrainStreamMessage;
}

export default function MapPage() {
  const [selected, setSelected] = useState<SelectedTrain | null>(null);

  const { data: trainsData } = useQuery({
    queryKey: ["trains-list-map"],
    queryFn: () => trainsApi.list({ page_size: 100 }),
    refetchInterval: 60_000,
  });

  const { lastMessage } = useTrainStream({ enabled: true });

  // Maintain a live positions map updated by WebSocket
  const [livePositions, setLivePositions] = useState<
    Map<string, TrainStreamMessage>
  >(new Map());

  useEffect(() => {
    if (!lastMessage) return;
    setLivePositions((prev) => {
      const next = new Map(prev);
      next.set(lastMessage.train_number, lastMessage);
      return next;
    });
    // Update selected if it's the same train
    setSelected((prev) => {
      if (!prev || prev.summary.train_number !== lastMessage.train_number) return prev;
      return { ...prev, liveMsg: lastMessage };
    });
  }, [lastMessage]);

  // Merge API data with live positions
  const mergedTrains = (trainsData?.trains ?? []).map((t) => {
    const live = livePositions.get(t.train_number);
    if (!live) return t;
    return {
      ...t,
      latitude: live.latitude,
      longitude: live.longitude,
      speed_kmh: live.speed_kmh ?? t.speed_kmh,
      current_delay_min: live.current_delay_min,
      next_station: live.next_station,
      status:
        live.current_delay_min <= 5
          ? "on_time"
          : live.current_delay_min <= 30
          ? "delayed"
          : "severely_delayed",
    };
  });

  const selectedSpeed = selected?.liveMsg?.speed_kmh ?? selected?.summary?.speed_kmh;

  return (
    <main className="page" style={{ overflow: "hidden" }}>
      <div className="relative h-[calc(100vh-60px)] w-full">
        {/* Map */}
        <LiveMap
          trains={mergedTrains}
          onTrainSelect={(t) =>
            setSelected({ summary: t, liveMsg: livePositions.get(t.train_number) })
          }
        />

        {/* Legend */}
        <div className="absolute bottom-4 left-4 z-10 glass rounded-xl p-3 text-xs">
          <div className="mb-1.5 font-medium text-gray-400">Delay status</div>
          <div className="flex flex-col gap-1">
            {[
              { cls: "bg-emerald-600", label: "On time (≤5 min)" },
              { cls: "bg-amber-600", label: "Delayed (5–30 min)" },
              { cls: "bg-red-600", label: "Severe (>30 min)" },
            ].map(({ cls, label }) => (
              <div key={label} className="flex items-center gap-1.5">
                <span className={`h-2.5 w-2.5 rounded-full ${cls}`} />
                <span className="text-gray-500">{label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Count badge */}
        <div className="absolute left-4 top-4 z-10 glass rounded-lg px-3 py-1.5 text-xs text-gray-400">
          <span className="font-medium text-white">{mergedTrains.filter(t => t.latitude).length}</span> trains tracked
        </div>

        {/* Side panel for selected train */}
        {selected && (
          <div className="absolute right-0 top-0 z-10 h-full w-80 glass-strong border-l border-white/5 p-5 overflow-y-auto animate-fade-in">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="font-bold text-white text-sm">{selected.summary.name}</h2>
                <p className="text-xs text-gray-500">{selected.summary.train_number}</p>
              </div>
              <button
                onClick={() => setSelected(null)}
                className="rounded-lg p-1 hover:bg-white/5 text-gray-500 hover:text-white transition"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <DelayBadge
              delayMin={selected.liveMsg?.current_delay_min ?? selected.summary.current_delay_min}
              status={selected.summary.status}
            />

            <div className="mt-4 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-500">Route</span>
                <span className="text-gray-300">
                  {selected.summary.source_station} → {selected.summary.destination_station}
                </span>
              </div>
              {(selected.liveMsg?.next_station ?? selected.summary.next_station) && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Next stop</span>
                  <span className="text-indigo-400">
                    {selected.liveMsg?.next_station ?? selected.summary.next_station}
                  </span>
                </div>
              )}
              {selectedSpeed != null && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-500">Live Speed</span>
                  <span className="inline-flex items-center gap-1.5 font-semibold text-white">
                    <span className={`h-1.5 w-1.5 rounded-full ${selectedSpeed > 2 ? "bg-emerald-400 animate-pulse" : "bg-amber-400"}`} />
                    {selectedSpeed > 2 ? `${Math.round(selectedSpeed)} km/h` : "Halted (0 km/h)"}
                  </span>
                </div>
              )}
            </div>

            {selected.liveMsg?.upcoming_stops && selected.liveMsg.upcoming_stops.length > 0 && (
              <div className="mt-5">
                <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">
                  Upcoming stops
                </h3>
                <div className="space-y-2">
                  {selected.liveMsg.upcoming_stops.slice(0, 4).map((s) => (
                    <div key={s.station_code} className="flex justify-between text-xs">
                      <span className="text-gray-400">{s.station_name}</span>
                      <span className="tabular-nums text-white">
                        {new Date(s.predicted_eta).toLocaleTimeString("en-IN", {
                          hour: "2-digit",
                          minute: "2-digit",
                          hour12: false,
                        })}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <Link
              href={`/train/${selected.summary.train_number}`}
              className="btn-primary mt-6 w-full justify-center text-sm"
              id={`map-panel-detail-${selected.summary.train_number}`}
            >
              Full ETA Detail
              <ExternalLink className="h-3.5 w-3.5" />
            </Link>
          </div>
        )}
      </div>
    </main>
  );
}
