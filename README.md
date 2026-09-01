# RailPredict AI

> Dynamic ETA Forecasting for Indian Coaching Trains  
> SIH 2026 · Problem Statement SIH26028 · Ministry of Railways

---

## What this is

A production-architecture implementation of an AI-powered train ETA prediction system. 4-layer ML ensemble (physics baseline → XGBoost residual → GRU → Kalman filter), real-time WebSocket updates, SHAP-based explainability, and delay propagation across connected trains.

**This is not a demo.** Every number displayed in the UI comes from a real API call. Auth and roles are enforced server-side. At least one real train flows through the same pipeline as simulated ones.

---

## Current phase: **Complete**

| Phase | Status | Description |
|-------|--------|-------------|
| 0 — Foundations | ✅ **Done** | Monorepo, auth, deployed skeleton |
| 1 — Data Spine | ✅ **Done** | Schema, simulator, ingestion |
| 2 — Baseline ETA | ✅ **Done** | Physics model + map UI |
| 3 — ML Layer | ✅ **Done** | XGBoost + SHAP explainability |
| 4 — Sequence + Kalman | ✅ **Done** | GRU + real-time correction |
| 5 — Propagation | ✅ **Done** | Cross-train delay cascade |
| 6 — Control Room | ✅ **Done** | RBAC + admin event injection |
| 7 — Hardening | ✅ **Done** | Load test, security, observability |

---

## Quick start (local)

```bash
# 1. Clone and copy env
git clone https://github.com/your-org/railpredict.git
cd railpredict
cp .env.example .env
# Edit .env — set at minimum: JWT_SECRET_KEY, DB_PASSWORD

# 2. Start the full stack
cd infra
docker compose up --build

# 3. Verify
curl http://localhost:8000/healthz   # → {"status":"ok"}
curl http://localhost:8000/readyz    # → {"status":"ok","db":"connected"}
open http://localhost:3000           # landing page with live API badge
```

---

## Repository structure

```
railpredict/
├── apps/web/              # Next.js 14 (App Router) + TypeScript + Tailwind
├── services/
│   ├── api/               # FastAPI: auth, trains, stations, realtime gateway
│   ├── ml-inference/      # FastAPI: feature engineering + model serving (Phase 3+)
│   ├── simulator/         # Background worker: digital twin (Phase 1+)
│   └── training/          # Offline batch training + evaluation (Phase 3+)
├── db/migrations/         # Alembic migrations
├── infra/
│   └── docker-compose.yml
├── docs/architecture.md   # Living spec — read this first
├── render.yaml            # Render deployment blueprint
├── DEPLOYMENT.md          # Step-by-step deploy guide
└── .github/workflows/ci.yml
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| API | FastAPI, SQLAlchemy (async), Alembic |
| Database | PostgreSQL + TimescaleDB + PostGIS |
| Streaming | Redis Streams (→ Kafka in Track 2) |
| ML | XGBoost, PyTorch (GRU), NumPy (Kalman) |
| Deploy | Vercel (web), Render (API), Timescale Cloud, Upstash Redis |
| CI/CD | GitHub Actions |
| Monitoring | Sentry |

---

## Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for the full step-by-step guide.

Live URLs (fill in after deploy):
- **Frontend**: `https://railpredict.vercel.app`  
- **API**: `https://railpredict-api.onrender.com`

---

## Architecture

Full architecture document at [`docs/architecture.md`](./docs/architecture.md).

---

## License

MIT
