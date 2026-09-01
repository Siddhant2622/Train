"use client";

import { StopEta, LivePosition } from "@/lib/api";
import { format, parseISO } from "date-fns";
import { Train, Navigation, AlertTriangle, CheckCircle2, Clock } from "lucide-react";

interface TrainTimelineProps {
  stops: StopEta[];
  livePosition: LivePosition | null;
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
  if (min <= 0) return <span className="text-emerald-400 font-medium">On time</span>;
  if (min <= 30) return <span className="text-amber-400 font-medium">+{Math.round(min)} min</span>;
  return <span className="text-red-400 font-medium">+{Math.round(min)} min</span>;
}

export function TrainTimeline({ stops, livePosition }: TrainTimelineProps) {
  if (!stops.length) {
    return (
      <div className="py-8 text-center text-sm text-gray-500">
        No upcoming stops — train may have reached its destination.
      </div>
    );
  }

  // Determine if the train is currently between stations
  const isBetweenStations = livePosition && livePosition.last_station && livePosition.next_station;

  return (
    <div className="relative pl-6 py-4 mx-2">
      {/* The main vertical line connecting all stations */}
      <div className="absolute left-[1.3rem] top-8 bottom-8 w-[2px] bg-indigo-900/40" />

      <div className="space-y-6 relative">
        {/* If GPS is active and train position is known, show live tracking banner */}
        {isBetweenStations && (
          <div className="relative z-10 flex gap-4 bg-indigo-950/30 p-4 rounded-xl border border-indigo-500/40 shadow-[0_0_25px_rgba(79,70,229,0.2)] overflow-hidden">
            <div className="absolute top-0 right-0 -mr-10 -mt-10 w-32 h-32 bg-indigo-500/10 rounded-full blur-2xl" />
            
            <div className={`absolute -left-[2.1rem] flex h-8 w-8 items-center justify-center rounded-full ${
              (livePosition.speed_kmh || 0) > 2 ? "bg-indigo-600 shadow-[0_0_15px_rgba(79,70,229,0.8)] animate-pulse" : "bg-amber-600 shadow-[0_0_10px_rgba(217,119,6,0.6)]"
            } text-white`}>
              <Train className="h-4 w-4" />
            </div>
            
            <div className="flex-1">
              <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-400 flex items-center gap-1.5">
                  <Navigation className="h-3 w-3" />
                  Live Train Telemetry
                </span>
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full border ${
                    (livePosition.speed_kmh || 0) > 2
                      ? "bg-emerald-950/60 border-emerald-800/60 text-emerald-400"
                      : "bg-amber-950/60 border-amber-800/60 text-amber-400"
                  }`}>
                    <span className={`h-1.5 w-1.5 rounded-full ${
                      (livePosition.speed_kmh || 0) > 2 ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
                    }`} />
                    {(livePosition.speed_kmh || 0) > 2 ? `${Math.round(livePosition.speed_kmh || 0)} km/h` : "Halted (0 km/h)"}
                  </span>
                </div>
              </div>
              <p className="text-sm text-gray-200">
                {(livePosition.speed_kmh || 0) > 2 ? (
                  <>En route between <strong className="text-white">{livePosition.last_station}</strong> and <strong className="text-white">{livePosition.next_station}</strong></>
                ) : (
                  <>Halted at station <strong className="text-white">{livePosition.last_station}</strong> (Next: <strong className="text-white">{livePosition.next_station}</strong>)</>
                )}
              </p>
              {livePosition.distance_to_next_km != null && (
                <div className="mt-3 flex items-center gap-2">
                  <div className="h-1.5 flex-1 bg-white/10 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-400 rounded-full transition-all duration-500" 
                      style={{ width: `${Math.min(100, Math.max(8, 100 - (livePosition.distance_to_next_km / 120) * 100))}%` }} 
                    />
                  </div>
                  <span className="text-xs text-gray-400 font-medium tabular-nums">
                    {livePosition.distance_to_next_km.toFixed(1)} km to next halt
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Render all stops */}
        {stops.map((stop) => {
          const isDeparted = stop.status === "departed";
          const isAtStation = stop.status === "at-station";

          return (
            <div key={stop.station_code} className="relative z-10 flex items-start gap-5 group">
              {/* Timeline node */}
              <div className={`absolute -left-[1.05rem] mt-2 h-3.5 w-3.5 rounded-full border-2 transition-transform group-hover:scale-125 ${
                isDeparted 
                  ? "border-emerald-500 bg-emerald-950" 
                  : isAtStation 
                    ? "border-amber-400 bg-amber-950 animate-pulse" 
                    : "border-indigo-500 bg-gray-900"
              }`} />
              
              <div className={`flex-1 rounded-xl p-4 border transition-all ${
                isDeparted
                  ? "bg-white/[0.02] border-white/5 opacity-70 hover:opacity-100"
                  : isAtStation
                    ? "bg-amber-950/20 border-amber-500/30 shadow-[0_0_15px_rgba(245,158,11,0.1)]"
                    : "bg-white/5 border-white/10 hover:border-indigo-500/40 hover:bg-white/[0.07]"
              }`}>
                {/* Station Info & Badges */}
                <div className="flex justify-between items-start flex-wrap gap-2">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-base font-bold text-white group-hover:text-indigo-400 transition-colors">
                        {stop.station_name}
                      </h3>
                      <span className="px-1.5 py-0.5 rounded bg-white/10 text-gray-300 font-mono text-xs font-semibold">
                        {stop.station_code}
                      </span>
                      {stop.platform && (
                        <span className="px-2 py-0.5 rounded-md bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-xs font-bold">
                          {stop.platform}
                        </span>
                      )}
                      {isDeparted && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-2 py-0.5 rounded">
                          <CheckCircle2 className="h-3 w-3" />
                          Departed
                        </span>
                      )}
                      {isAtStation && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-400 bg-amber-950/50 border border-amber-800/50 px-2 py-0.5 rounded animate-pulse">
                          At Platform
                        </span>
                      )}
                    </div>
                    {stop.distance_km != null && stop.distance_km > 0 && (
                      <p className="text-xs text-gray-500 mt-0.5">{stop.distance_km.toFixed(1)} km from origin</p>
                    )}
                  </div>

                  <div className="text-right">
                    <div className="text-lg font-bold text-white tabular-nums flex items-center justify-end gap-1.5">
                      <Clock className="h-3.5 w-3.5 text-indigo-400" />
                      {fmtTime(stop.predicted_eta)}
                    </div>
                    {stop.scheduled_arrival && (
                      <div className="text-xs text-gray-400">
                        Sched: <span className="line-through">{fmtTime(stop.scheduled_arrival)}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Status & Delay */}
                <div className="mt-2.5 flex items-center justify-between border-t border-white/5 pt-2 flex-wrap gap-2">
                  <div className="text-sm">
                    {fmtDelay(stop.delay_min)}
                  </div>
                  {stop.lower_bound && stop.upper_bound && (
                    <div className="text-[11px] text-gray-400 tabular-nums">
                      Confidence: {fmtTime(stop.lower_bound)} – {fmtTime(stop.upper_bound)}
                    </div>
                  )}
                </div>

                {/* AI / ML Analysis Factors */}
                {stop.explanation?.shap_factors && stop.explanation.shap_factors.length > 0 && (
                  <div className="mt-3 bg-indigo-950/30 border border-indigo-900/40 rounded-lg p-2.5">
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-indigo-400/90 mb-1.5 flex items-center gap-1.5">
                      <AlertTriangle className="h-3 w-3" />
                      AI Delay Factors
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {stop.explanation.shap_factors.map((factor: string, idx: number) => {
                        const isNegative = factor.includes("decreased") || factor.includes("-");
                        return (
                          <span 
                            key={idx} 
                            className={`text-[10px] px-2 py-0.5 rounded border ${
                              isNegative 
                                ? "bg-emerald-950/40 border-emerald-800/40 text-emerald-400" 
                                : "bg-amber-950/40 border-amber-800/40 text-amber-300"
                            }`}
                          >
                            {factor}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
