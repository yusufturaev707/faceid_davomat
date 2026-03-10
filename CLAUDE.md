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
- Config in `backend/app/core/config.py`
- Migrations in `backend/alembic/versions/`

## Architecture

### Backend (`backend/app/`)

- **`main.py`** — FastAPI app, CORS config, lifespan (loads InsightFace model on startup in background thread)
- **`api/v1/endpoints/`** — Route handlers: `auth.py`, `photo.py`, `admin.py`
- **`core/config.py`** — All settings via Pydantic BaseSettings (JWT, DB URL, photo validation params)
- **`core/security.py`** — JWT creation/verification, bcrypt hashing, `get_current_user` dependency
- **`services/face_service.py`** — Core ML logic: base64 decode → InsightFace detection → age/background/dimension validation → WebP storage
- **`models/`** — SQLAlchemy ORM: `User`, `VerificationLog`, `RefreshToken`
- **`crud/`** — DB queries separated by model
- **`db/session.py`** — SQLAlchemy session factory

### Frontend (`frontend/src/`)

- **`api.ts`** — Axios instance with token injection and refresh interceptor
- **`contexts/AuthContext.tsx`** — Global auth state, login/logout
- **`tokenStore.ts`** — localStorage token helpers
- **`pages/`** — `LoginPage`, `VerifyPage` (operator use), `DashboardPage`/`LogsPage`/`LogDetailPage` (admin only)

### Key Data Flow

1. **Photo verification:** Client POSTs `{ img_b64, age }` → `photo.py` → `face_service.py` validates face count, age (±5y tolerance), dimensions (354×472px), background (white corners RGB>200), color palette → saves WebP + thumbnail to `uploads/verifications/` → logs to `verification_logs` table.

2. **Auth:** Login → JWT access token (30 min) + refresh token in DB (7 days). Frontend refresh interceptor auto-rotates tokens.

3. **Roles:** `admin` can access `/api/v1/admin/*` (logs, stats, user management). `operator` role only accesses verify endpoint.

### Photo Validation Parameters (configurable in `config.py`)

| Setting | Default |
|---|---|
| `REQUIRED_WIDTH` | 354 |
| `REQUIRED_HEIGHT` | 472 |
| `AGE_TOLERANCE` | 5 |
| `MIN_PALITRA_VALUE` | 50 |
| `WEBP_QUALITY` | 80 |
| `THUMBNAIL_SIZE` | 150 |

### InsightFace Model

- Loaded once at startup as singleton (`buffalo_l` variant)
- Background thread loading with threading `Event` to signal readiness
- ONNX Runtime inference (CPU by default)
- Stored under InsightFace cache directory (auto-downloaded on first run)


# Systemd service sifatida ishlatish
celery -A app.celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  --max-tasks-per-child=100
