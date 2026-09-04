# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

FaceID / davomat (attendance) platform for national exam sessions: FastAPI + InsightFace backend,
React/TS admin panel, two aiogram Telegram bots, and PyQt6 desktop clients (separate repo) at the
exam centers. All UI text, comments and error messages are in **Uzbek** — match that when editing.

Repo layout: `backend/` (API + Celery), `frontend/` (Vite/React admin), `davomat_bot/` (attendance
bot), `statistic_bot/` (admissions-stats bot), `deploy/` (systemd units + frontend deploy script),
`API_DOCS.md` (external `X-API-Key` contract for third-party systems — the root `README.md` is only
a two-endpoint excerpt of it).

## Commands

**Backend** (`cd backend`, venv in `backend/venv`):
- Dev server: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Celery (two queues, run both — also listed in `celery_commands.py`):
  `celery -A app.celery_app worker -Q verify --pool=threads --concurrency=4 --loglevel=info`
  and `celery -A app.celery_app worker -Q storage --pool=threads --concurrency=8 --loglevel=info`
- Celery beat (token/login cleanup): `celery -A app.celery_app beat --loglevel=info`
- Migrations: `alembic upgrade head` · new: `alembic revision --autogenerate -m "..."`
- Single-head check (run before committing a migration): `python scripts/check_alembic_single_head.py`
- Seed roles + admin: `python -m app.db.seed` (password from `ADMIN_INITIAL_PASSWORD`, else random to stdout)
- Seed statistic-bot users: `python -m app.db.seed_statistic_bot` (reads `ADMIN_IDS` / `STAFF_IDS` out of
  `statistic_bot/.env`; idempotent one-shot — afterwards users are managed in the admin panel)
- Tests: `pytest` · single file `pytest tests/unit/test_permissions_catalog.py` · single test `pytest tests/unit/test_api_key_hashing.py::test_name -x`
- Local stack: `docker compose up -d` (from `backend/` — postgres 16, redis 7, api, two celery workers)

**Frontend** (`cd frontend`): `npm run dev` (5173, proxies `/api/v1` → `127.0.0.1:8000`), `npm run build`
(`tsc -b && vite build`), `npm run test` (vitest), `npm run test:watch`. `npm run lint` is declared but
**eslint is not in devDependencies** — it fails until installed.

**Bots** — each has its own `.venv` and `requirements.txt`, and must be run from its own directory:
`cd davomat_bot && python main.py` · `cd statistic_bot && python bot.py`.

**Prod**: gunicorn + uvicorn workers over a unix socket (`backend/gunicorn_config.py`), systemd units in
`deploy/systemd/` (`sudo deploy/systemd/install.sh` installs them; paths are hardcoded to
`/var/www/faceid_davomat`). Frontend: `sudo bash deploy/frontend-deploy.sh` (git pull → `npm ci` → build →
rsync into the nginx web root → `nginx -t` + reload).

## Configuration

`backend/.env` (see `.env.example`). `app/config.py` is the single Settings source — `app/core/config.py`
is a deprecated re-export. Many fields have **no default and are required**, and a validator rejects
`SECRET_KEY`/`API_KEY_PEPPER` shorter than 32 chars or matching known placeholders: with a bad `.env`
the app refuses to start rather than running insecurely. DB defaults to
`postgresql://postgres:4144@localhost:5432/faceid_db`.

Each bot has its own `.env` next to its `config.py` (`BOT_TOKEN`, `API_BASE_URL`, `API_KEY`).

## Architecture

**Request pipeline** (`app/main.py`): SecurityHeaders → RequestId/access-log/metrics → slowapi rate
limiter → CORS → `api_router` under `/api/v1`. Lifespan does a DB ping, `sync_permission_catalog()`, then
starts InsightFace loading in a background thread. `/metrics` (Prometheus text) is 404 unless
`METRICS_AUTH_TOKEN` is set, then requires a bearer token.

**Auth** (`app/dependencies.py`): `X-API-Key` **or** `Authorization: Bearer` — sending both is a 400
(header-injection guard). JWT `jti` is checked against a Redis blacklist so logout takes effect
immediately. Refresh tokens are hashed (SHA-256) with a `family_id`; rotation keeps the family and
revokes the old token — reuse detection lives there, and `online_users.py` derives "who is online"
from those families. Frontend keeps the access token in `sessionStorage` (`src/tokenStore.ts`), the
refresh token in an HttpOnly cookie, sends `X-CSRF-Token` from a readable cookie on mutating requests,
and de-dupes concurrent refreshes into one promise (`refreshTokensOnce` in `src/api.ts`).

**Permissions** — the core cross-cutting concern:
- `app/core/permissions.py` (`class P`) is the single source of truth. Endpoints use
  `Depends(PermissionChecker(P.X.code))`; `role_key == 1` (admin) bypasses every check.
- `app/core/permission_sync.py` runs on every startup: adds new codenames, updates existing names,
  grants all of them to the admin role, backfills split-off permissions from their source permission,
  and deletes codenames listed in `_REMOVED_PERMISSIONS`. Adding a permission = add to `P` + restart;
  no seed re-run needed.
- `frontend/src/permissions.ts` mirrors the same codename strings by hand — **change both together**;
  `frontend/src/permissions.test.ts` guards the frontend side.
- Access is separate from *scope*: `app/core/region_scope.py` decides which region's rows a user may
  see (`student:all_regions` permission, else the user's own `region_id`). Endpoints call both.

**Exam-session state machine** (`app/crud/test_session.py`, keys 1–5: created → loading → embedding →
active → finished). `PATCH /test-sessions/{id}/state` is the orchestration point: key=2 dispatches the
student-loader Celery task, key=3 dispatches embedding extraction, key=4 refuses to activate unless
every student is `is_ready` and rolls the state back otherwise. Transitions that start heavy jobs
require extra permissions beyond `test_session:update`. Progress for both long jobs is written to
Redis and polled by the frontend (`/student-load-progress`, `/embedding-progress`).

**Face pipeline** (`app/services/face_service.py`): `FaceAnalysis("buffalo_l")` on ONNX Runtime CPU,
loaded once per *process* as a module singleton guarded by a `threading.Event` — never touch the model
before the event is set. Celery loads its own copy per worker/child (`worker_process_init`), so the
FastAPI singleton is not shared. `FACE_ONNX_INTRA_THREADS=1` is deliberate: one core per inference so
`EMBEDDING_WORKERS` threads can run inferences in parallel (`services/embedding_extractor.py`, which
streams students in chunks of 500 to bound memory).

**Celery** (`app/celery_app.py`): `verify` queue = CPU-bound face work, `storage` queue = fire-and-forget
image writes. `visibility_timeout` is raised to 9h because the 700k-student loader runs for hours and
Redis would otherwise redeliver it to a second worker. `POST /photo/verify-photo` checks Redis queue
length first and returns 429 + `Retry-After` under backpressure, then returns a `task_id` the client
polls. Embedding extraction (`/embedding/extract`) is the exception — synchronous, off-thread, no Celery.

**Layering**: `api/v1/endpoints/*` (HTTP + permissions) → `crud/*` (SQLAlchemy queries, `CRUDBase`
generic) and `services/*` (business logic, Excel/PDF export, external HTTP) → `models/*` (SQLAlchemy 2.0
`Mapped[]` declarative). Reference tables (regions, zones, tests, smenas, states, reasons, genders,
blacklist) are all served by `endpoints/lookup.py` with per-table permissions.

**Telegram bots** — both are aiogram 3, long polling, in-memory FSM, and hold **no DB connection**:
everything goes through the backend over HTTP with one shared `X-API-Key` and a single reused
`aiohttp.ClientSession` (`davomat_bot/services/api_client.py`, `statistic_bot/services/backend_client.py`).
That key authenticates the *bot*, not the person — per-request authorization is by `telegram_id` against
`/davomat-bot/check/{id}` and `/statistic-bot/check/{id}`. Bot users are **not** `users` rows and have no
permission codenames; the two tables use deliberately different role models:
- `DavomatBot.role_id` → FK to `roles`, plus a `davomat_bot_regions` M2M. CRUD enforces that
  `role_key == 4` gets exactly one region, other roles one or more.
- `StatisticBot.role` is a bare int (1 Admin / 2 Rahbar / 3 Xodim), no FK — roles 2 and 3 hide payment
  status and 2025 data, enforced bot-side.

Admin CRUD for both lives under `/admin/davomat-bots` and `/admin/statistic-bots`
(`DavomatBotsPage` / `StatisticBotsPage` in the frontend). The davomat flow — documented in full in the
`endpoints/davomat_bot.py` module docstring — is `/ready-sessions` → pick day+smena → `/face-verify`
(ID-card QR decoded with `zxing-cpp` into `ps_ser`/`jshshir`, selfie compared against the GTSP photo,
plus a DB check that the student really belongs to *that* smena) → `/mark-attendance`
(`Student.is_entered=True` + `StudentLog` UPSERT, keeping the `bulk_create_student_logs` invariants).
`/find-by-jshshir` + `/remove-attendance` undo attendance without touching `StudentLog` history;
`handlers/cheat.py` writes `CheatingLog` rows.

**Frontend** (React 18 + TS + Tailwind, react-router v6): routes nest `ProtectedRoute` → `Layout` →
`PermissionRoute`, which takes `permission` / `anyOf` / `allOf` plus a `redirectTo`. `HomeRedirect` in
`App.tsx` picks the landing page from the user's permissions — its condition must stay identical to the
`/test-dashboard` route guard or `/` becomes a redirect loop. In-page elements use `PermissionGate` and
the `usePermission()` hook; `AuthContext` holds the user and their permission list. **The frontend has no
admin bypass** — it relies on permission sync having granted admin everything, while the backend
`PermissionChecker` short-circuits on `role_key == 1`. Revoke a permission from the admin role by hand
and the UI hides the feature while the API still allows it (`isAdmin` is for UI banners only).
`LookupCrudPage` is the generic table/form behind every reference-table page.

**External systems**: student rosters stream in from CEFR/MS/IIV/OTM-DTM APIs (`services/student_loader.py`,
paginated, `bulk_insert_mappings`), zones sync from the OTM buildings API (`services/zone_sync.py` —
`Zone.building_id` is the *external* building id, not `Zone.id`), passport photos come from GTSP
(`services/gtsp_client.py`). All are driven by `API_*` settings and return 503 when unset.

## Gotchas

- Two alembic directories exist. `alembic.ini` points at **`app/db/migrations`** — that is the live one.
  `backend/alembic/` is a stale leftover; don't add revisions there.
- `tests/conftest.py` sets required env vars before importing settings and swaps the DB for SQLite
  (`StaticPool`); tests never touch postgres. Stray empty `tests/unit.py` / `tests/integration.py` files
  sit next to the real package dirs — the packages are what pytest collects. Coverage is thin (three test
  files), so most changes are verified by running the stack, not by the suite.
- `davomat_bot/config.py` accepts a tuple of env files and falls back to `.env.example` when `.env` is
  missing — a bot with no `.env` starts anyway on the committed example credentials instead of failing
  loudly. `statistic_bot/.env` is committed and is what `seed_statistic_bot` reads.
- Datetimes are timezone-aware (`TIMESTAMP(timezone=True)`); several migrations exist purely to convert
  naive columns. Keep new datetime columns tz-aware.
- `StudentLog.first_captured` / `last_captured` are raw BYTEA selfies — `SELECT *` on that table is expensive.
- `/api/v1/health`, `/api/v1/healthcheck` and the root `/health` are unauthenticated and hit by desktop
  clients every few seconds; gunicorn filters all three out of the access log. Keep them I/O-free.
- Root `Dockerfile` and root `docker-compose.yml` are empty — the real ones live in `backend/`.
