"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Search, Train, Map, Activity, ArrowRight, Cpu, Zap, Shield } from "lucide-react";

const FEATURES = [
  {
    icon: Zap,
    title: "Physics-First ETA",
    desc: "Layer 1 baseline from track physics — section speeds, halt times, distance. No black boxes.",
  },
  {
    icon: Cpu,
    title: "ML Ensemble (Phase 3)",
    desc: "XGBoost residuals + GRU sequence model + Kalman filter correction layered on the physics base.",
  },
  {
    icon: Map,
    title: "Live Fleet Map",
    desc: "MapLibre GL map with real-time train positions, delay heat colors, and click-to-detail.",
  },
  {
    icon: Activity,
    title: "SHAP Explainability",
    desc: "Every ETA ships with a reason — which factors caused the delay, in plain language.",
  },
  {
    icon: Shield,
    title: "Role-Based Access",
    desc: "Passengers see ETAs. Controllers see the full picture and inject disruption events.",
  },
  {
    icon: Train,
    title: "Delay Propagation",
    desc: "A delay on one train triggers predictions for every connected train at shared sections.",
  },
];

const ROADMAP = [
  { phase: "0", label: "Foundations", status: "done" },
  { phase: "1", label: "Data Spine", status: "done" },
  { phase: "2", label: "Baseline ETA + Map", status: "done" },
  { phase: "3", label: "XGBoost + SHAP", status: "done" },
  { phase: "4", label: "GRU + Kalman", status: "active" },
  { phase: "5", label: "Delay Propagation", status: "upcoming" },
  { phase: "6", label: "Control Room", status: "upcoming" },
];

export default function HomePage() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    if (/^\d{4,5}$/.test(q)) {
      router.push(`/train/${q}`);
    } else {
      router.push(`/stations/${q.toUpperCase()}`);
    }
  }

  return (
    <main className="page bg-grid bg-radial-glow">
      {/* Hero */}
      <section className="container flex min-h-[calc(100vh-60px)] flex-col items-center justify-center py-20 text-center">
        <div className="animate-fade-up">
          <span className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-800/60 bg-indigo-950/40 px-4 py-1.5 text-xs font-medium text-indigo-400">
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse" />
            Physics ETA · ML Ensemble · Live Map
          </span>

          <h1 className="mb-6 text-5xl font-bold leading-tight tracking-tight sm:text-6xl lg:text-7xl">
            <span className="hero-gradient-text">RailPredict AI</span>
          </h1>

          <p className="mb-10 max-w-2xl text-lg text-gray-400">
            Dynamic ETA forecasting for Indian coaching trains. Every number on
            screen comes from a real model, a real database, and a real
            algorithm — not a hard-coded array.
          </p>

          {/* Search */}
          <form onSubmit={handleSearch} className="relative mx-auto mb-8 w-full max-w-md">
            <Search className="absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-500" />
            <input
              id="train-search-input"
              className="search-input"
              placeholder="Train number (12301) or station code (NDLS)…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoComplete="off"
            />
            <button
              type="submit"
              className="btn-primary absolute right-2 top-1/2 -translate-y-1/2 px-3 py-1.5 text-sm"
            >
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>

          <div className="flex flex-wrap justify-center gap-3">
            <a href="/dashboard" className="btn-primary" id="hero-cta-dashboard">
              <Activity className="h-4 w-4" />
              Control Room
            </a>
            <a href="/map" className="btn-ghost" id="hero-cta-map">
              <Map className="h-4 w-4" />
              Live Map
            </a>
          </div>
        </div>

        {/* Quick train links */}
        <div className="mt-12 flex flex-wrap justify-center gap-2 text-xs text-gray-600">
          <span>Try:</span>
          {["12301", "12393", "12951", "12001", "12309"].map((n) => (
            <a
              key={n}
              href={`/train/${n}`}
              className="rounded-md border border-white/5 bg-white/3 px-2 py-1 text-indigo-400 transition hover:border-indigo-800/60 hover:bg-indigo-950/30"
            >
              {n}
            </a>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="container pb-24">
        <h2 className="mb-2 text-center text-2xl font-bold text-white">How it works</h2>
        <p className="mb-10 text-center text-sm text-gray-500">
          Four-layer ensemble. Every layer is independently testable and replaceable.
        </p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="glass glow-hover rounded-xl p-5">
              <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600/15">
                <Icon className="h-4.5 w-4.5 text-indigo-400" />
              </div>
              <h3 className="mb-1.5 font-semibold text-white">{title}</h3>
              <p className="text-sm leading-relaxed text-gray-500">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Roadmap */}
      <section className="container pb-24">
        <h2 className="mb-10 text-center text-2xl font-bold text-white">Build roadmap</h2>
        <div className="mx-auto flex max-w-2xl flex-col gap-3">
          {ROADMAP.map(({ phase, label, status }) => (
            <div
              key={phase}
              className={`flex items-center gap-4 rounded-xl border px-5 py-3 transition ${
                status === "done"
                  ? "border-emerald-800/40 bg-emerald-950/20"
                  : status === "active"
                  ? "border-indigo-700/60 bg-indigo-950/30 shadow-[0_0_20px_rgba(99,102,241,0.1)]"
                  : "border-white/5 bg-white/[0.01] opacity-60"
              }`}
            >
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  status === "done"
                    ? "bg-emerald-600 text-white"
                    : status === "active"
                    ? "bg-indigo-600 text-white"
                    : "border border-white/10 text-gray-600"
                }`}
              >
                {phase}
              </span>
              <span
                className={`flex-1 font-medium ${
                  status === "done" ? "text-emerald-400" : status === "active" ? "text-white" : "text-gray-600"
                }`}
              >
                Phase {phase} — {label}
              </span>
              <span className="text-xs text-gray-700 capitalize">{status.replace("_", " ")}</span>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
