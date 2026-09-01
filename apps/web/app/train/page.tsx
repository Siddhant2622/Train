"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Search, Train, ChevronLeft, ChevronRight, Clock, AlertTriangle } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

interface TrainSummary {
  train_number: string;
  name: string;
  train_type: string | null;
  source_station: string;
  destination_station: string;
  current_delay_min: number;
  status: string;
  latitude?: number | null;
  longitude?: number | null;
  speed_kmh?: number | null;
  next_station: string | null;
  last_updated: string | null;
}

interface TrainListResponse {
  trains: TrainSummary[];
  total: number;
  page: number;
  page_size: number;
}

function TrainsDirectoryContent() {
  const searchParams = useSearchParams();
  const initialQ = searchParams.get("q") || "";
  const [searchTerm, setSearchTerm] = useState(initialQ);
  const [debouncedSearch, setDebouncedSearch] = useState(initialQ);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
      setPage(1); // Reset page on new search
    }, 500);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const { data, isLoading, isError } = useQuery<TrainListResponse>({
    queryKey: ["trains", debouncedSearch, page],
    queryFn: async () => {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const url = new URL("/api/v1/trains", baseUrl);
      url.searchParams.set("page", page.toString());
      url.searchParams.set("page_size", pageSize.toString());
      if (debouncedSearch) {
        url.searchParams.set("q", debouncedSearch);
      }
      const res = await fetch(url.toString());
      if (!res.ok) throw new Error("Failed to fetch trains");
      return res.json();
    },
  });

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  return (
    <main className="page bg-grid bg-radial-glow min-h-screen">
      <div className="container py-12">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Trains Directory</h1>
            <p className="text-gray-400">
              Browse {data ? data.total.toLocaleString() : "all"} trains in the network.
            </p>
          </div>

          <div className="relative w-full sm:w-96">
            <Search className="absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              placeholder="Search by number or name..."
              className="search-input w-full pl-10"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>

        <div className="glass rounded-xl border border-white/5 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-white/5 text-xs uppercase text-gray-400">
                <tr>
                  <th className="px-6 py-4 font-medium">Train</th>
                  <th className="px-6 py-4 font-medium">Number</th>
                  <th className="px-6 py-4 font-medium">Route</th>
                  <th className="px-6 py-4 font-medium">Live Status</th>
                  <th className="px-6 py-4 font-medium text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {isLoading ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                      <div className="flex justify-center">
                        <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
                      </div>
                      <span className="mt-3 block">Loading trains...</span>
                    </td>
                  </tr>
                ) : isError ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center text-red-400">
                      Error loading trains. Please try again.
                    </td>
                  </tr>
                ) : data?.trains.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                      No trains found matching "{debouncedSearch}"
                    </td>
                  </tr>
                ) : (
                  data?.trains.map((train) => (
                    <tr key={train.train_number} className="hover:bg-white/[0.02] transition-colors group">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-600/20 text-indigo-400">
                            <Train className="h-5 w-5" />
                          </div>
                          <div>
                            <div className="font-semibold text-gray-200">{train.name}</div>
                            {train.train_type && (
                              <span className="text-xs text-gray-500">
                                {train.train_type}
                              </span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 font-mono font-medium text-gray-300">
                        {train.train_number}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-col">
                          <span className="text-gray-300">{train.source_station} → {train.destination_station}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2 flex-wrap">
                          {train.status === "on_time" ? (
                            <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
                              <Clock className="h-4 w-4" />
                              <span>On Time</span>
                            </div>
                          ) : train.status === "delayed" || train.status === "severely_delayed" ? (
                            <div className={`flex items-center gap-1.5 font-medium ${train.status === "severely_delayed" ? "text-red-400" : "text-amber-400"}`}>
                              <AlertTriangle className="h-4 w-4" />
                              <span>{Math.round(train.current_delay_min)} min late</span>
                            </div>
                          ) : (
                            <span className="text-gray-500">Scheduled</span>
                          )}

                          {train.speed_kmh != null && (
                            <span className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded font-medium ${
                              train.speed_kmh > 2
                                ? "bg-emerald-950/50 border border-emerald-800/50 text-emerald-400"
                                : "bg-gray-900 border border-gray-800 text-gray-400"
                            }`}>
                              <span className={`h-1.5 w-1.5 rounded-full ${train.speed_kmh > 2 ? "bg-emerald-400 animate-pulse" : "bg-gray-500"}`} />
                              {train.speed_kmh > 2 ? `${Math.round(train.speed_kmh)} km/h` : "Halted"}
                            </span>
                          )}
                        </div>
                        {train.next_station && (
                          <div className="mt-1 text-xs text-gray-500">
                            Next: <span className="text-gray-400">{train.next_station}</span>
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link 
                          href={`/train/${train.train_number}`}
                          className="inline-flex items-center rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-gray-300 transition-colors hover:bg-white/10 hover:text-white"
                        >
                          View Status
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {!isLoading && !isError && totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-white/5 bg-white/[0.01] px-6 py-4">
              <div className="text-sm text-gray-400">
                Showing <span className="font-medium text-gray-200">{((page - 1) * pageSize) + 1}</span> to{" "}
                <span className="font-medium text-gray-200">
                  {Math.min(page * pageSize, data!.total)}
                </span>{" "}
                of <span className="font-medium text-gray-200">{data!.total}</span>
              </div>
              
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-gray-400 transition hover:bg-white/10 hover:text-white disabled:opacity-50 disabled:hover:bg-white/5 disabled:hover:text-gray-400"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <div className="text-sm font-medium text-gray-300 px-2">
                  {page} / {totalPages}
                </div>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-gray-400 transition hover:bg-white/10 hover:text-white disabled:opacity-50 disabled:hover:bg-white/5 disabled:hover:text-gray-400"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

export default function TrainsDirectory() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-grid bg-radial-glow flex items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" /></div>}>
      <TrainsDirectoryContent />
    </Suspense>
  );
}
