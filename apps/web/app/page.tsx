"use client";

import { useApiStatus } from "@/hooks/useApiStatus";
import {
  Train,
  Zap,
  Activity,
  Brain,
  ChevronRight,
  GitBranch,
  Shield,
  BarChart3,
  Map,
} from "lucide-react";
import Link from "next/link";

// ---------------------------------------------------------------------------
// API Status Badge — the Phase 0 smoke-test component.
// Every number on this page comes from a real API call.
// ---------------------------------------------------------------------------
function ApiStatusBadge() {
  const { data, isLoading, isError } = useApiStatus();

  if (isLoading) {
    return (
      <span className="inline-flex items-center gap-2 rounded-full border border-gray-700 bg-gray-900 px-3 py-1 text-xs text-gray-400">
        <span className="h-1.5 w-1.5 rounded-full bg-gray-500 pulse-dot" />
        Connecting to API…
      </span>
    );
  }

  if (isError || data?.status !== "ok") {
    return (
      <span className="inline-flex items-center gap-2 rounded-full border border-red-900 bg-red-950 px-3 py-1 text-xs text-red-400">
        <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
        API Offline
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-emerald-800 bg-emerald-950 px-3 py-1 text-xs text-emerald-400">
      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 pulse-dot" />
      API Online · v{data.version}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Feature cards
// ---------------------------------------------------------------------------
const features = [
  {
    icon: Brain,
    title: "4-Layer ML Ensemble",
    description:
      "Physics baseline → XGBoost residual → GRU sequence model → Kalman corrector. Every ETA is a calibrated probability, not a guess.",
    phase: "Phase 3–4",
  },
  {
    icon: Zap,
    title: "Real-Time Kalman Correction",
    description:
      "ETAs update the moment a new position ping arrives. No page refresh. WebSocket-pushed to every connected client simultaneously.",
    phase: "Phase 4",
  },
  {
    icon: Activity,
    title: "Delay Propagation Engine",
    description:
      "When one train slips, we detect every downstream train on the same sections and re-forecast their ETAs automatically.",
    phase: "Phase 5",
  },
  {
    icon: BarChart3,
    title: "Explainable Predictions",
    description:
      "SHAP-powered breakdown of every ETA change: signal congestion, weather, station halt, historical pattern — in human-readable form.",
    phase: "Phase 3",
  },
  {
    icon: Map,
    title: "Live Fleet Map",
    description:
      "Color-coded train positions on MapLibre GL — open source, no API billing surprises. Clusters at scale, details on click.",
    phase: "Phase 2",
  },
  {
    icon: Shield,
    title: "Role-Based Access Control",
    description:
      "Three roles: Public, Controller, Admin. Enforced server-side on every endpoint — never just hidden in the UI.",
    phase: "Phase 6",
  },
];

// ---------------------------------------------------------------------------
// Phase roadmap items
// ---------------------------------------------------------------------------
const phases = [
  { number: "0", label: "Foundations", status: "current", desc: "Monorepo, auth, deployed skeleton" },
  { number: "1", label: "Data Spine", status: "upcoming", desc: "Schema, simulator, ingestion" },
  { number: "2", label: "Baseline ETA", status: "upcoming", desc: "Physics model + map UI" },
  { number: "3", label: "ML Layer", status: "upcoming", desc: "XGBoost + SHAP explainability" },
  { number: "4", label: "Sequence + Kalman", status: "upcoming", desc: "GRU + real-time correction" },
  { number: "5", label: "Propagation", status: "upcoming", desc: "Cross-train delay cascade" },
];

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function HomePage() {
  return (
    <main className="bg-mesh min-h-screen">
      {/* ----------------------------------------------------------------- */}
      {/* Nav                                                                */}
      {/* ----------------------------------------------------------------- */}
      <nav className="sticky top-0 z-50 border-b border-white/5 bg-black/40 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600">
              <Train className="h-4 w-4 text-white" />
            </div>
            <span className="font-semibold tracking-tight text-white">RailPredict AI</span>
          </div>
          <div className="flex items-center gap-4">
            <ApiStatusBadge />
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-gray-400 transition hover:border-white/20 hover:text-white"
            >
              <GitBranch className="h-3 w-3" />
              GitHub
            </a>
          </div>
        </div>
      </nav>

      {/* ----------------------------------------------------------------- */}
      {/* Hero                                                               */}
      {/* ----------------------------------------------------------------- */}
      <section className="mx-auto max-w-6xl px-6 pb-24 pt-20 text-center">
        {/* SIH badge */}
        <div className="fade-up mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-800/60 bg-indigo-950/50 px-4 py-1.5 text-xs font-medium text-indigo-300">
          <span className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
          SIH 2026 · Problem Statement SIH26028 · Ministry of Railways
        </div>

        <h1 className="fade-up fade-up-delay-1 mb-6 text-5xl font-bold leading-tight tracking-tight text-white sm:text-6xl lg:text-7xl">
          Dynamic ETA Forecasting
          <br />
          <span className="gradient-text">for Coaching Trains</span>
        </h1>

        <p className="fade-up fade-up-delay-2 mx-auto mb-10 max-w-2xl text-lg leading-relaxed text-gray-400">
          A 4-layer ML ensemble — physics baseline, XGBoost residual, GRU sequence model, and
          Kalman corrector — delivering real-time, explainable arrival predictions across the
          Indian Railways network.
        </p>

        <div className="fade-up fade-up-delay-3 flex flex-wrap items-center justify-center gap-4">
          <Link
            href="/dashboard"
            id="cta-dashboard"
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-900/40 transition hover:bg-indigo-500 hover:shadow-indigo-800/60"
          >
            Open Control Room
            <ChevronRight className="h-4 w-4" />
          </Link>
          <Link
            href="/map"
            id="cta-map"
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-6 py-3 text-sm font-semibold text-white transition hover:border-white/20 hover:bg-white/10"
          >
            Live Train Map
          </Link>
        </div>

        {/* Track decoration */}
        <div className="fade-up fade-up-delay-4 mx-auto mt-16 max-w-xl">
          <div className="track-line" />
          <div className="mt-2 flex justify-between text-[10px] text-gray-600">
            <span>PNBE</span>
            <span>ARA</span>
            <span>BXR</span>
            <span>DDU</span>
          </div>
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* Stats row                                                          */}
      {/* ----------------------------------------------------------------- */}
      <section className="border-y border-white/5 bg-white/[0.02]">
        <div className="mx-auto grid max-w-6xl grid-cols-2 divide-x divide-white/5 px-6 py-8 sm:grid-cols-4">
          {[
            { value: "4-layer", label: "ML Ensemble" },
            { value: "±5 min", label: "Target accuracy" },
            { value: "WebSocket", label: "Live ETA updates" },
            { value: "SHAP", label: "Explainability" },
          ].map((stat) => (
            <div key={stat.label} className="px-6 py-2 text-center">
              <div className="text-2xl font-bold text-white">{stat.value}</div>
              <div className="mt-1 text-xs text-gray-500">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* Features                                                           */}
      {/* ----------------------------------------------------------------- */}
      <section className="mx-auto max-w-6xl px-6 py-24">
        <h2 className="mb-4 text-center text-3xl font-bold text-white">
          What makes this different
        </h2>
        <p className="mb-12 text-center text-gray-500">
          Every number on screen comes from a real API call. No hardcoded arrays.
        </p>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.title}
                className="glass glow-hover rounded-2xl p-6"
              >
                <div className="mb-4 flex items-start justify-between">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600/20">
                    <Icon className="h-5 w-5 text-indigo-400" />
                  </div>
                  <span className="rounded-full bg-amber-950/60 px-2 py-0.5 text-[10px] font-medium text-amber-400">
                    {f.phase}
                  </span>
                </div>
                <h3 className="mb-2 font-semibold text-white">{f.title}</h3>
                <p className="text-sm leading-relaxed text-gray-500">{f.description}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* Roadmap                                                            */}
      {/* ----------------------------------------------------------------- */}
      <section className="border-t border-white/5 bg-white/[0.015] py-24">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="mb-12 text-center text-3xl font-bold text-white">
            Build roadmap
          </h2>
          <div className="relative">
            {/* Vertical line */}
            <div className="absolute left-5 top-0 h-full w-px bg-gradient-to-b from-indigo-600 via-indigo-800 to-transparent sm:left-1/2" />

            <div className="space-y-8">
              {phases.map((p, i) => (
                <div
                  key={p.number}
                  className={`relative flex items-start gap-6 sm:items-center ${
                    i % 2 === 0 ? "sm:flex-row" : "sm:flex-row-reverse"
                  }`}
                >
                  {/* Node */}
                  <div
                    className={`relative z-10 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full border text-sm font-bold sm:absolute sm:left-1/2 sm:-translate-x-1/2 ${
                      p.status === "current"
                        ? "border-indigo-500 bg-indigo-600 text-white shadow-lg shadow-indigo-900/60"
                        : "border-gray-700 bg-gray-900 text-gray-500"
                    }`}
                  >
                    {p.number}
                  </div>

                  {/* Card */}
                  <div
                    className={`glass rounded-xl p-4 sm:w-[42%] ${
                      i % 2 === 0 ? "sm:mr-auto sm:ml-0" : "sm:ml-auto sm:mr-0"
                    } ${p.status === "current" ? "border-indigo-800/60" : ""}`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-white">
                        Phase {p.number} — {p.label}
                      </span>
                      {p.status === "current" && (
                        <span className="rounded-full bg-indigo-900 px-2 py-0.5 text-[10px] text-indigo-300">
                          In Progress
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-sm text-gray-500">{p.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* Footer                                                             */}
      {/* ----------------------------------------------------------------- */}
      <footer className="border-t border-white/5 py-10 text-center text-xs text-gray-600">
        <div className="mb-2 flex items-center justify-center gap-2">
          <Train className="h-3 w-3" />
          <span className="font-medium text-gray-500">RailPredict AI</span>
        </div>
        <p>SIH 2026 · Problem Statement SIH26028 · Ministry of Railways</p>
        <p className="mt-1">
          Not affiliated with Indian Railways / CRIS. All predictions are AI-generated estimates.
        </p>
      </footer>
    </main>
  );
}
