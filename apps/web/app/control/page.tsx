"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { admin, FleetSummary, ApiError } from "@/lib/api";

export default function ControlRoomPage() {
  const router = useRouter();
  const [summary, setSummary] = useState<FleetSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Event form state
  const [eventType, setEventType] = useState("speed_restriction");
  const [stationCode, setStationCode] = useState("");
  const [severity, setSeverity] = useState("high");
  const [delayImpact, setDelayImpact] = useState(30);
  const [notes, setNotes] = useState("");
  const [injecting, setInjecting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const data = await admin.fleetSummary();
        setSummary(data);
      } catch (err: any) {
        if (err instanceof ApiError && err.status === 401) {
          router.push("/login");
        } else {
          setError(err.detail || "Failed to load Control Room");
        }
      }
    };
    fetchSummary();
    const interval = setInterval(fetchSummary, 30000);
    return () => clearInterval(interval);
  }, [router]);

  const handleInject = async (e: React.FormEvent) => {
    e.preventDefault();
    setInjecting(true);
    setSuccess(null);
    setError(null);
    
    try {
      await admin.createEvent({
        event_type: eventType,
        station_code: stationCode,
        severity,
        speed_restriction_kmh: eventType === "speed_restriction" ? 20 : null,
        delay_impact_min: delayImpact,
        notes,
      });
      setSuccess(`Event successfully injected at ${stationCode}`);
      setStationCode("");
      setNotes("");
    } catch (err: any) {
      setError(err.detail || "Failed to inject event");
    } finally {
      setInjecting(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    router.push("/");
  };

  if (!summary && !error) {
    return (
      <div className="flex h-screen items-center justify-center text-gray-400">
        Authenticating...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 p-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-8 flex items-center justify-between border-b border-gray-800 pb-4">
          <div>
            <h1 className="text-3xl font-bold text-red-500 flex items-center gap-2">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
              </span>
              Control Room
            </h1>
            <p className="text-gray-400 mt-1">Admin overrides and live disruption injections.</p>
          </div>
          <button 
            onClick={handleLogout}
            className="rounded bg-gray-800 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700"
          >
            Logout
          </button>
        </div>

        {error && (
          <div className="mb-6 rounded-lg bg-red-900/50 p-4 border border-red-800/50 text-red-200">
            {error}
          </div>
        )}
        
        {success && (
          <div className="mb-6 rounded-lg bg-green-900/50 p-4 border border-green-800/50 text-green-200">
            {success}
          </div>
        )}

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          {/* KPI Dashboard */}
          <div className="col-span-1 lg:col-span-2 grid grid-cols-2 gap-4">
            <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
              <div className="text-sm text-gray-400">Active Trains</div>
              <div className="mt-2 text-4xl font-bold text-white">{summary?.total_active || 0}</div>
            </div>
            <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
              <div className="text-sm text-gray-400">On Time %</div>
              <div className="mt-2 text-4xl font-bold text-green-400">{summary?.on_time_percentage || 0}%</div>
            </div>
            <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
              <div className="text-sm text-gray-400">Average Delay</div>
              <div className="mt-2 text-4xl font-bold text-yellow-400">{summary?.avg_delay_min || 0}m</div>
            </div>
            <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
              <div className="text-sm text-gray-400">Severely Delayed</div>
              <div className="mt-2 text-4xl font-bold text-red-400">{summary?.severely_delayed || 0}</div>
            </div>
          </div>

          {/* Injection Panel */}
          <div className="col-span-1 rounded-xl border border-red-900/50 bg-gray-900/50 p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Inject Disruption Event</h2>
            <form onSubmit={handleInject} className="flex flex-col gap-4">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Event Type</label>
                <select 
                  className="w-full rounded bg-gray-800 p-2 text-white border border-gray-700"
                  value={eventType}
                  onChange={e => setEventType(e.target.value)}
                >
                  <option value="speed_restriction">Speed Restriction</option>
                  <option value="station_closure">Station Closure</option>
                  <option value="track_maintenance">Track Maintenance</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-gray-400 mb-1 block">Station Code</label>
                <input 
                  required
                  placeholder="e.g. NDLS"
                  className="w-full rounded bg-gray-800 p-2 text-white border border-gray-700"
                  value={stationCode}
                  onChange={e => setStationCode(e.target.value.toUpperCase())}
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Severity</label>
                  <select 
                    className="w-full rounded bg-gray-800 p-2 text-white border border-gray-700"
                    value={severity}
                    onChange={e => setSeverity(e.target.value)}
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Delay (mins)</label>
                  <input 
                    type="number"
                    min="1"
                    required
                    className="w-full rounded bg-gray-800 p-2 text-white border border-gray-700"
                    value={delayImpact}
                    onChange={e => setDelayImpact(Number(e.target.value))}
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-gray-400 mb-1 block">Admin Notes</label>
                <textarea 
                  className="w-full rounded bg-gray-800 p-2 text-white border border-gray-700 h-20"
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                />
              </div>

              <button 
                type="submit"
                disabled={injecting}
                className="mt-2 w-full rounded bg-red-600 p-3 font-semibold text-white hover:bg-red-500 disabled:opacity-50 transition-colors"
              >
                {injecting ? "Injecting..." : "Inject Event"}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
