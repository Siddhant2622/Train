/**
 * useTrainStream — WebSocket hook with auto-reconnect (exponential backoff).
 *
 * Connects to /ws/trains/{number} or /ws/fleet and exposes the latest message.
 * Reconnects automatically on disconnect with exponential backoff up to 30s.
 */

"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { getApiBase } from "@/lib/api";

export interface TrainStreamMessage {
  event: string;
  train_number: string;
  run_date: string;
  timestamp: string;
  latitude: number | null;
  longitude: number | null;
  speed_kmh: number;
  current_delay_min: number;
  last_station: string;
  next_station: string;
  upcoming_stops: Array<{
    station_code: string;
    station_name: string;
    predicted_eta: string;
    lower_bound: string;
    upper_bound: string;
    delay_min: number;
    explanation?: Record<string, any>;
  }>;
}

interface UseTrainStreamOptions {
  trainNumber?: string;  // undefined = fleet stream
  enabled?: boolean;
}

interface UseTrainStreamResult {
  lastMessage: TrainStreamMessage | null;
  connected: boolean;
  error: string | null;
}

export function useTrainStream({
  trainNumber,
  enabled = true,
}: UseTrainStreamOptions = {}): UseTrainStreamResult {
  const [lastMessage, setLastMessage] = useState<TrainStreamMessage | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(1000);
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  const getWsUrl = useCallback(() => {
    const base = getApiBase().replace(/^http/, "ws");
    return trainNumber ? `${base}/ws/trains/${trainNumber}` : `${base}/ws/fleet`;
  }, [trainNumber]);

  const connect = useCallback(() => {
    if (!enabled || !mountedRef.current) return;

    const url = getWsUrl();
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      setConnected(true);
      setError(null);
      backoffRef.current = 1000;
      // Keepalive ping every 25s
      pingRef.current = setInterval(() => ws.send("ping"), 25_000);
    };

    ws.onmessage = (ev) => {
      if (!mountedRef.current) return;
      if (ev.data === "pong") return;
      try {
        const msg = JSON.parse(ev.data) as TrainStreamMessage;
        setLastMessage(msg);
      } catch {}
    };

    ws.onerror = () => {
      setError("WebSocket error");
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setConnected(false);
      if (pingRef.current) clearInterval(pingRef.current);

      const delay = Math.min(backoffRef.current, 30_000);
      backoffRef.current = Math.min(backoffRef.current * 2, 30_000);
      setTimeout(connect, delay);
    };
  }, [enabled, getWsUrl]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      if (pingRef.current) clearInterval(pingRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { lastMessage, connected, error };
}
