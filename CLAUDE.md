# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FaceID Verification API — a facial recognition system for ID photo verification. FastAPI backend with InsightFace ML model + React/TypeScript frontend. UI text is in Uzbek.

## Commands

### Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Seed admin user
python -m app.db.seed

# Run dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Celery worker
celery -A app.celery_app worker --loglevel=info --concurrency=4 --max-tasks-per-child=100

# Docker bilan ishga tushirish
docker compose up -d
```

### Frontend

```bash
cd frontend

npm install
npm run dev       # dev server on port 5173
npm run build     # production build
npm run preview   # preview production build
```

### Database

- PostgreSQL required. Default: `postgresql://postgres:4144@localhost:5432/faceid_db`
- Config in `backend/app/config.py`
- Migrations in `backend/app/db/migrations/versions/`

## Architecture

### Backend (`backend/app/`)

- **`main.py`** — FastAPI app, CORS config, lifespan, exception handlers, logging
- **`config.py`** — All settings via Pydantic BaseSettings (JWT, DB URL, photo validation params)
- **`dependencies.py`** — Global dependencies: `get_db`, `get_current_user`, `get_current_active_user`, `require_admin`
- **`celery_app.py`** — Celery configuration with InsightFace model loading per worker
- **`api/v1/endpoints/`** — Route handlers: `auth.py`, `photo.py`, `admin.py`, `embedding.py`
- **`api/v1/router.py`** — Aggregates all v1 endpoint routers
- **`core/security.py`** — JWT creation/verification, bcrypt hashing (pure utility functions)
- **`core/exceptions.py`** — Global exception handlers (validation, HTTP, unhandled)
- **`core/logging.py`** — Structured logging configuration
- **`services/face_service.py`** — Core ML logic: base64 decode, InsightFace detection, validation, WebP storage
- **`models/`** — SQLAlchemy ORM: `User`, `VerificationLog`, `RefreshToken`, `VerifyFaces`, `ApiKey`
- **`schemas/`** — Pydantic request/response schemas
- **`crud/`** — DB queries separated by model, `base.py` has generic CRUD class
- **`db/session.py`** — SQLAlchemy engine and session factory
- **`db/base.py`** — SQLAlchemy DeclarativeBase
- **`db/migrations/`** — Alembic migrations
- **`tasks/verify_task.py`** — Celery tasks for async photo/face verification

### Frontend (`frontend/src/`)

- **`api.ts`** — Axios instance with token injection and refresh interceptor
- **`interfaces.ts`** — TypeScript interfaces matching backend schemas
- **`tokenStore.ts`** — In-memory access token storage (XSS safe)
- **`contexts/AuthContext.tsx`** — Global auth state, login/logout
- **`contexts/ThemeContext.tsx`** — Dark/light mode theme state
- **`components/`** — `Layout`, `Sidebar`, `ProtectedRoute`, `AdminRoute`, `Pagination`, etc.
- **`pages/`** — `LoginPage`, `VerifyPage`, `VerifyTwoFacePage`, `EmbeddingPage`, `DashboardPage`, `LogsPage`, `FaceLogsPage`, `ApiKeysPage`, `SettingsPage`

### Key Data Flow

1. **Photo verification:** Client POSTs `{ img_b64, age }` → `photo.py` → Celery task → `face_service.py` validates face, age (±tolerance), dimensions, background, palette → saves WebP + thumbnail → logs to DB → returns via task status polling.

2. **Two-face verification:** Client POSTs `{ ps_img, lv_img }` → Celery task → detects faces in both images → cosine similarity comparison → logs result.

3. **Auth:** Login → JWT access token (30 min) + HttpOnly refresh token cookie (7 days). Frontend refresh interceptor auto-rotates tokens. API key auth also supported via `X-API-Key` header.

4. **Roles:** `admin` can access `/api/v1/admin/*` (logs, stats, user management, API keys). `operator` role only accesses verify/embedding endpoints.

### InsightFace Model

- Loaded once at startup as singleton (`buffalo_l` variant)
- Background thread loading with threading `Event` to signal readiness
- ONNX Runtime inference (CPU by default)
- Stored under InsightFace cache directory (auto-downloaded on first run)
