# CLAUDE.md

FaceID Verification API — FastAPI + InsightFace backend, React/TS frontend. UI text is in Uzbek.

## Commands

**Backend** (`cd backend`):
- Dev server: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Celery: `celery -A app.celery_app worker --loglevel=info --concurrency=4 --max-tasks-per-child=100`
- Migrations: `alembic upgrade head`
- Seed admin: `python -m app.db.seed`
- Docker: `docker compose up -d`

**Frontend** (`cd frontend`): `npm run dev` (port 5173), `npm run build`

**DB:** PostgreSQL, default `postgresql://postgres:4144@localhost:5432/faceid_db` (configured in `app/config.py`).

## Non-obvious notes

- **InsightFace model** (`buffalo_l`) is loaded once at startup as a singleton in a background thread, signaled via a threading `Event`. Don't call the model before the event is set. ONNX Runtime, CPU by default.
- **Auth:** JWT access token = 30 min, HttpOnly refresh cookie = 7 days, frontend auto-rotates via axios interceptor. API key auth also supported via `X-API-Key` header.
- **Roles:** `admin` → `/api/v1/admin/*`. `operator` → verify/embedding endpoints only.
- **Celery** loads its own InsightFace instance per worker — don't assume the FastAPI singleton is shared.
- **Photo verification** is async: endpoint queues a Celery task, client polls task status.
