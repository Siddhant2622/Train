/**
 * useApiStatus hook — polls /healthz once on mount to show the API status badge.
 * Uses React Query so the result is cached and not re-fetched on every render.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { health, type HealthResponse } from "@/lib/api";

export function useApiStatus() {
  return useQuery<HealthResponse, Error>({
    queryKey: ["api-status"],
    queryFn: health.liveness,
    retry: 2,
    staleTime: 30_000,   // treat as fresh for 30s
    refetchInterval: 60_000, // background refresh every 60s
  });
}
