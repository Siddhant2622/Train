/**
 * Updated API client — includes all Phase 2 endpoints.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(`API ${status}: ${detail}`);
    this.name = "ApiError";
  }
}

async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {}
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return {} as T;
  return response.json() as Promise<T>;
}

export const getApiBase = () => API_BASE;

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------
export interface HealthResponse { status: string; version?: string; db?: string; }
export const health = {
  liveness: () => apiRequest<HealthResponse>("/healthz"),
  readiness: () => apiRequest<HealthResponse>("/readyz"),
};

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
export interface TokenResponse {
  access_token: string; refresh_token: string; token_type: string; role: string;
}
export interface UserPublic { id: string; email: string; role: string; is_active: boolean; }

export const auth = {
  login: (email: string, password: string) =>
    apiRequest<TokenResponse>("/api/v1/auth/login", {
      method: "POST", body: JSON.stringify({ email, password }),
    }),
  refresh: (refresh_token: string) =>
    apiRequest<TokenResponse>("/api/v1/auth/refresh", {
      method: "POST", body: JSON.stringify({ refresh_token }),
    }),
  me: () => apiRequest<UserPublic>("/api/v1/auth/me"),
};

// ---------------------------------------------------------------------------
// Trains
// ---------------------------------------------------------------------------
export interface LivePosition {
  latitude: number | null;
  longitude: number | null;
  speed_kmh: number | null;
  last_station: string | null;
  next_station: string | null;
  distance_to_next_km: number | null;
  current_delay_min: number;
  updated_at: string;
  source: string;
  status?: string | null;
  status_message?: string | null;
  distance_covered_km?: number | null;
  total_distance_km?: number | null;
  is_halted?: boolean;
}

export interface StopEta {
  station_code: string;
  station_name: string;
  sequence: number;
  scheduled_arrival: string | null;
  scheduled_departure?: string | null;
  predicted_eta: string;
  lower_bound: string;
  upper_bound: string;
  confidence: number;
  delay_min: number;
  platform?: string | null;
  distance_km?: number | null;
  is_halt?: boolean;
  status?: string;
  explanation?: Record<string, any>;
}

export interface TrainSummary {
  train_number: string;
  name: string;
  train_type: string | null;
  source_station: string;
  destination_station: string;
  current_delay_min: number;
  status: string;
  latitude: number | null;
  longitude: number | null;
  speed_kmh?: number | null;
  next_station: string | null;
  last_updated: string | null;
}

export interface TrainDetail {
  train_number: string;
  name: string;
  train_type: string | null;
  zone: string | null;
  source_station: string;
  destination_station: string;
  total_distance_km: number | null;
  run_date: string | null;
  position: LivePosition | null;
  upcoming_stops: StopEta[];
  model_version: string;
  coach_position?: string | null;
  status?: string | null;
  total_halts?: number | null;
  avg_speed_kmh?: number | null;
}

export interface TrainListResponse {
  trains: TrainSummary[];
  total: number;
  page: number;
  page_size: number;
}


export const trains = {
  list: (params?: { page?: number; page_size?: number; zone?: string; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.page_size) qs.set("page_size", String(params.page_size));
    if (params?.zone) qs.set("zone", params.zone);
    if (params?.status) qs.set("status", params.status);
    return apiRequest<TrainListResponse>(`/api/v1/trains?${qs}`);
  },
  get: (number: string) => apiRequest<TrainDetail>(`/api/v1/trains/${number}`),
  history: (number: string, limit = 100) =>
    apiRequest<{ train_number: string; run_date: string; positions: any[] }>(
      `/api/v1/trains/${number}/history?limit=${limit}`
    ),
  schedule: (number: string) =>
    apiRequest<{ train_number: string; stops: any[] }>(`/api/v1/trains/${number}/schedule`),
};

// ---------------------------------------------------------------------------
// Stations
// ---------------------------------------------------------------------------
export interface Station {
  station_code: string; name: string; city: string | null; state: string | null;
  zone: string | null; latitude: number; longitude: number;
  is_major: boolean; platform_count: number | null;
}
export interface ArrivalEntry {
  train_number: string; train_name: string; train_type: string | null;
  scheduled_arrival: string | null; predicted_eta: string | null;
  delay_min: number; status: string; source_station: string; destination_station: string;
}
export interface StationArrivalsResponse {
  station_code: string; station_name: string; arrivals: ArrivalEntry[]; generated_at: string;
}

export const stations = {
  list: (params?: { zone?: string; major_only?: boolean }) => {
    const qs = new URLSearchParams();
    if (params?.zone) qs.set("zone", params.zone);
    if (params?.major_only) qs.set("major_only", "true");
    return apiRequest<Station[]>(`/api/v1/stations?${qs}`);
  },
  get: (code: string) => apiRequest<Station>(`/api/v1/stations/${code}`),
  arrivals: (code: string, limit = 20) =>
    apiRequest<StationArrivalsResponse>(`/api/v1/stations/${code}/arrivals?limit=${limit}`),
};

// ---------------------------------------------------------------------------
// Admin
// ---------------------------------------------------------------------------
export interface FleetSummary {
  total_active: number; on_time: number; delayed: number; severely_delayed: number;
  avg_delay_min: number; max_delay_min: number; on_time_percentage: number; generated_at: string;
}

export const admin = {
  fleetSummary: () => apiRequest<FleetSummary>("/api/v1/admin/fleet-summary"),
  createEvent: (data: any) =>
    apiRequest<any>("/api/v1/admin/events", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};


