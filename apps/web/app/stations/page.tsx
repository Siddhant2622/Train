"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Search, MapPin, ChevronLeft, ChevronRight } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

interface Station {
  station_code: string;
  name: string;
  city: string | null;
  state: string | null;
  zone: string | null;
  is_major: boolean;
  platform_count: number | null;
}

interface StationListResponse {
  stations: Station[];
  total: number;
  page: number;
  page_size: number;
}

export default function StationsDirectory() {
  const [searchTerm, setSearchTerm] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
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

  const { data, isLoading, isError } = useQuery<StationListResponse>({
    queryKey: ["stations", debouncedSearch, page],
    queryFn: async () => {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const url = new URL("/api/v1/stations", baseUrl);
      url.searchParams.set("page", page.toString());
      url.searchParams.set("page_size", pageSize.toString());
      if (debouncedSearch) {
        url.searchParams.set("q", debouncedSearch);
      }
      const res = await fetch(url.toString());
      if (!res.ok) throw new Error("Failed to fetch stations");
      return res.json();
    },
  });

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  return (
    <main className="page bg-grid bg-radial-glow min-h-screen">
      <div className="container py-12">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Stations Directory</h1>
            <p className="text-gray-400">
              Browse {data ? data.total.toLocaleString() : "all"} railway stations in the network.
            </p>
          </div>

          <div className="relative w-full sm:w-96">
            <Search className="absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              placeholder="Search by code, name, or city..."
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
                  <th className="px-6 py-4 font-medium">Station</th>
                  <th className="px-6 py-4 font-medium">Code</th>
                  <th className="px-6 py-4 font-medium">Location</th>
                  <th className="px-6 py-4 font-medium">Zone</th>
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
                      <span className="mt-3 block">Loading stations...</span>
                    </td>
                  </tr>
                ) : isError ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center text-red-400">
                      Error loading stations. Please try again.
                    </td>
                  </tr>
                ) : data?.stations.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                      No stations found matching "{debouncedSearch}"
                    </td>
                  </tr>
                ) : (
                  data?.stations.map((station) => (
                    <tr key={station.station_code} className="hover:bg-white/[0.02] transition-colors group">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
                            station.is_major ? "bg-indigo-600/20 text-indigo-400" : "bg-white/5 text-gray-400"
                          }`}>
                            <MapPin className="h-5 w-5" />
                          </div>
                          <div>
                            <div className="font-semibold text-gray-200">{station.name}</div>
                            {station.is_major && (
                              <span className="text-[10px] font-medium tracking-wider text-indigo-400 uppercase">
                                Major Station
                              </span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 font-mono font-medium text-gray-300">
                        {station.station_code}
                      </td>
                      <td className="px-6 py-4">
                        {station.city ? (
                          <div className="flex flex-col">
                            <span className="text-gray-300">{station.city}</span>
                            <span className="text-xs text-gray-500">{station.state}</span>
                          </div>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {station.zone ? (
                          <span className="inline-flex rounded-full bg-white/5 px-2.5 py-1 text-xs font-medium text-gray-300 border border-white/10">
                            {station.zone}
                          </span>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link 
                          href={`/stations/${station.station_code}`}
                          className="inline-flex items-center rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-gray-300 transition-colors hover:bg-white/10 hover:text-white"
                        >
                          View Board
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
