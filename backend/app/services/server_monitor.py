"""Server va FaceID tizimi monitoringi (`/admin/server-monitor`, faqat superadmin).

Bitta Debian serverda API (gunicorn), Celery (verify/storage/beat), botlar,
PostgreSQL, Redis va nginx birga ishlaydi — shuning uchun hamma narsa shu
jarayon ichidan o'qiladi: `psutil` (CPU/RAM/disk/tarmoq/jarayonlar),
`systemctl show` (unit holati), `journalctl`, Postgres `pg_stat_*`
ko'rinishlari, Redis `INFO` va Celery `inspect`.

Qoidalar:
- Faqat o'qish. Servisni to'xtatish/qayta ishga tushirish YO'Q — bu
  sahifa kuzatish uchun; boshqaruv serverda `systemctl` bilan qoladi.
- Har bir bo'lim alohida yig'iladi va o'z xatosini qaytaradi: Redis
  o'chiq bo'lsa ham CPU/disk ko'rinaveradi (`_safe`).
- Og'ir narsalar chegaralangan: DB so'rovlariga `statement_timeout`,
  Celery `inspect` ga 1 s, log o'qish oxiridan va hajm chegarasi bilan.
- Jarayonlarning buyruq qatori (cmdline) faqat guruhlash uchun o'qiladi,
  javobga chiqmaydi — unda parol/token bo'lishi mumkin.
- Loglardagi tokenlar/kalitlar javobga chiqishdan oldin yashiriladi.

Yuklama tarixi — `tasks.monitor_sample` (Celery beat, har daqiqada)
`record_sample()` orqali Redis ro'yxatiga yozadi, 24 soat saqlanadi.
"""

import json
import logging
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import psutil
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import QueuePool

from app.config import settings

logger = logging.getLogger("faceid.services.server_monitor")

BACKEND_DIR = Path(__file__).resolve().parents[2]

# Yuklama tarixi: har daqiqada bitta nuqta, 24 soat.
HISTORY_KEY = "monitor:samples"
HISTORY_MAX = 1440
SAMPLE_INTERVAL_SECONDS = 60

# Faollik sanoqlari (DB COUNT'lar) shu muddat keshlanadi — sahifa har
# 15 s'da so'raydi, `student_logs` dagi vaqt ustunida indeks yo'q.
_ACTIVITY_CACHE_KEY = "monitor:activity"
_ACTIVITY_CACHE_TTL = 30

_DB_STATEMENT_TIMEOUT = "3s"
_CELERY_INSPECT_TIMEOUT = 1.0
_CPU_SAMPLE_SECONDS = 0.5
_TOP_PROCESSES = 12

# Ogohlantirish chegaralari (foiz).
_WARN_PCT = 85
_CRIT_PCT = 95


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ts(epoch: float | None) -> str | None:
    if not epoch:
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def _safe(fn: Callable[[], dict]) -> dict:
    """Bo'limni yig'ish; xato bo'lsa butun javob emas, faqat shu bo'lim yiqiladi."""
    try:
        return {"ok": True, **fn()}
    except Exception as exc:  # noqa: BLE001 — monitoring hech qachon 500 bermasin
        logger.warning("Monitoring bo'limi xatosi (%s): %s", fn.__name__, exc)
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:300]}


def configured_units() -> list[str]:
    units = []
    for raw in settings.MONITOR_SYSTEMD_UNITS.split(","):
        name = raw.strip()
        if not name:
            continue
        if "." not in name:
            name += ".service"
        units.append(name)
    return units


# ============================================================================
# Tizim: CPU, RAM, disk, tarmoq, jarayonlar
# ============================================================================

# Jarayonlarni FaceID komponentlariga ajratish. Tartib muhim — birinchi
# mos kelgan guruh olinadi.
_GROUPS: tuple[tuple[str, str], ...] = (
    ("api", "API (gunicorn)"),
    ("celery_verify", "Celery — verify"),
    ("celery_storage", "Celery — storage"),
    ("celery_beat", "Celery — beat"),
    ("celery_other", "Celery — boshqa"),
    ("davomat_bot", "Davomat bot"),
    ("statistic_bot", "Statistika bot"),
    ("postgres", "PostgreSQL"),
    ("redis", "Redis"),
    ("nginx", "Nginx"),
)
_GROUP_LABELS = dict(_GROUPS)


def _celery_queue(cmd: list[str]) -> str | None:
    for i, part in enumerate(cmd):
        if part in ("-Q", "--queues") and i + 1 < len(cmd):
            return cmd[i + 1]
        if part.startswith("--queues="):
            return part.split("=", 1)[1]
    return None


def classify_process(name: str, cmd: list[str]) -> str | None:
    """Jarayon qaysi FaceID komponentiga tegishli (yoki None)."""
    name = (name or "").lower()
    joined = " ".join(cmd).lower()
    if "celery" in joined:
        if "beat" in cmd:
            return "celery_beat"
        queue = _celery_queue(cmd) or ""
        if "verify" in queue:
            return "celery_verify"
        if "storage" in queue:
            return "celery_storage"
        return "celery_other"
    if "gunicorn" in joined or "uvicorn" in joined:
        return "api"
    if "davomat_bot" in joined:
        return "davomat_bot"
    if "statistic_bot" in joined:
        return "statistic_bot"
    if name.startswith("postgres") or name == "postmaster":
        return "postgres"
    if name.startswith("redis-server"):
        return "redis"
    if name == "nginx":
        return "nginx"
    return None


def _os_name() -> str:
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if line.startswith("PRETTY_NAME="):
                return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return platform.platform()


def _cpu_temperature() -> float | None:
    sensors = getattr(psutil, "sensors_temperatures", None)
    if sensors is None:
        return None
    try:
        temps = sensors()
    except Exception:  # noqa: BLE001
        return None
    values = [
        t.current
        for key in ("coretemp", "k10temp", "cpu_thermal", "zenpower")
        for t in temps.get(key, [])
        if t.current
    ]
    return round(max(values), 1) if values else None


def _disks() -> list[dict]:
    app_dir = str(BACKEND_DIR)
    parts = []
    seen: set[str] = set()
    for part in psutil.disk_partitions(all=False):
        if (
            part.fstype in ("", "squashfs", "tmpfs", "devtmpfs", "overlay")
            or "cdrom" in part.opts
            or part.mountpoint.startswith(("/snap", "/boot/efi"))
            or part.device in seen
        ):
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except OSError:
            continue
        seen.add(part.device)
        parts.append(
            {
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent,
                "contains_app": False,
            }
        )
    # Ilova (uploads, loglar) turgan bo'lim — eng uzun mos mountpoint.
    best = max(
        (p for p in parts if app_dir.lower().startswith(p["mountpoint"].lower())),
        key=lambda p: len(p["mountpoint"]),
        default=None,
    )
    if best is not None:
        best["contains_app"] = True
    return parts


def collect_system() -> dict:
    """CPU/RAM/disk/tarmoq + FaceID jarayon guruhlari va eng og'ir jarayonlar.

    CPU foizi `_CPU_SAMPLE_SECONDS` oralig'ida o'lchanadi; shu oraliqda
    tarmoq va disk I/O tezligi ham hisoblanadi (ikki o'lchov farqi).
    """
    attrs = ["pid", "name", "username", "cmdline", "memory_info", "num_threads", "create_time"]
    procs = list(psutil.process_iter(attrs))
    for p in procs:
        try:
            p.cpu_percent(None)
        except psutil.Error:
            pass
    net0 = psutil.net_io_counters()
    disk0 = psutil.disk_io_counters()
    t0 = time.monotonic()
    per_cpu = psutil.cpu_percent(interval=_CPU_SAMPLE_SECONDS, percpu=True)
    elapsed = max(time.monotonic() - t0, 1e-3)
    net1 = psutil.net_io_counters()
    disk1 = psutil.disk_io_counters()

    total_mem = psutil.virtual_memory().total
    groups: dict[str, dict] = {}
    rows = []
    for p in procs:
        try:
            cpu = p.cpu_percent(None)
        except psutil.Error:
            continue
        info = p.info
        if not info["pid"]:  # Windows "System Idle Process" — bo'sh CPU, jarayon emas
            continue
        mem = info.get("memory_info")
        rss = mem.rss if mem else 0
        group = classify_process(info.get("name") or "", info.get("cmdline") or [])
        row = {
            "pid": info["pid"],
            "name": info.get("name") or "?",
            "user": info.get("username"),
            "cpu_percent": round(cpu, 1),
            "rss": rss,
            "mem_percent": round(rss * 100 / total_mem, 2) if total_mem else 0,
            "threads": info.get("num_threads") or 0,
            "started_at": _ts(info.get("create_time")),
            "group": group,
        }
        rows.append(row)
        if group:
            g = groups.setdefault(
                group,
                {
                    "key": group,
                    "label": _GROUP_LABELS[group],
                    "processes": 0,
                    "cpu_percent": 0.0,
                    "rss": 0,
                    "started_at": row["started_at"],
                },
            )
            g["processes"] += 1
            g["cpu_percent"] = round(g["cpu_percent"] + cpu, 1)
            g["rss"] += rss
            # Eng eski jarayon — komponent qachondan beri ishlayotgani.
            if row["started_at"] and (not g["started_at"] or row["started_at"] < g["started_at"]):
                g["started_at"] = row["started_at"]

    top_cpu = sorted(rows, key=lambda r: r["cpu_percent"], reverse=True)[:_TOP_PROCESSES]
    top_mem = sorted(rows, key=lambda r: r["rss"], reverse=True)[:_TOP_PROCESSES]

    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    try:
        load1, load5, load15 = psutil.getloadavg()
    except (AttributeError, OSError):
        load1 = load5 = load15 = 0.0
    freq = None
    try:
        f = psutil.cpu_freq()
        freq = round(f.current) if f else None
    except Exception:  # noqa: BLE001
        pass
    boot = psutil.boot_time()

    def _rate(a, b, attr):
        if a is None or b is None:
            return None
        return max(0.0, (getattr(b, attr) - getattr(a, attr)) / elapsed)

    return {
        "host": {
            "hostname": socket.gethostname(),
            "os": _os_name(),
            "kernel": platform.release(),
            "arch": platform.machine(),
            "python": sys.version.split()[0],
            "boot_time": _ts(boot),
            "uptime_seconds": int(time.time() - boot),
            "server_time": _now().isoformat(),
        },
        "cpu": {
            "percent": round(sum(per_cpu) / len(per_cpu), 1) if per_cpu else 0.0,
            "per_cpu": [round(v, 1) for v in per_cpu],
            "cores_logical": psutil.cpu_count() or 0,
            "cores_physical": psutil.cpu_count(logical=False) or 0,
            "load_1": round(load1, 2),
            "load_5": round(load5, 2),
            "load_15": round(load15, 2),
            "freq_mhz": freq,
            "temperature_c": _cpu_temperature(),
        },
        "memory": {
            "total": vm.total,
            "available": vm.available,
            "used": vm.total - vm.available,
            "percent": vm.percent,
            "cached": getattr(vm, "cached", 0),
            "buffers": getattr(vm, "buffers", 0),
            "swap_total": sw.total,
            "swap_used": sw.used,
            "swap_percent": sw.percent,
        },
        "disks": _disks(),
        "network": {
            "bytes_sent": net1.bytes_sent if net1 else 0,
            "bytes_recv": net1.bytes_recv if net1 else 0,
            "sent_per_sec": _rate(net0, net1, "bytes_sent"),
            "recv_per_sec": _rate(net0, net1, "bytes_recv"),
            "errin": net1.errin if net1 else 0,
            "errout": net1.errout if net1 else 0,
            "dropin": net1.dropin if net1 else 0,
            "dropout": net1.dropout if net1 else 0,
            "connections": _tcp_connections(),
        },
        "disk_io": {
            "read_per_sec": _rate(disk0, disk1, "read_bytes"),
            "write_per_sec": _rate(disk0, disk1, "write_bytes"),
        },
        "process_count": len(procs),
        "groups": [groups[k] for k, _ in _GROUPS if k in groups],
        "top_cpu": top_cpu,
        "top_memory": top_mem,
    }


def _tcp_connections() -> dict | None:
    """TCP ulanishlar holati bo'yicha (ESTABLISHED, TIME_WAIT, ...)."""
    try:
        conns = psutil.net_connections(kind="tcp")
    except (psutil.AccessDenied, OSError):
        return None
    counts: dict[str, int] = {}
    for c in conns:
        counts[c.status] = counts.get(c.status, 0) + 1
    return counts


# ============================================================================
# systemd unitlari
# ============================================================================

_UNIT_PROPS = (
    "Id,Description,LoadState,ActiveState,SubState,MainPID,"
    "ActiveEnterTimestamp,NRestarts,MemoryCurrent,UnitFileState"
)


def _parse_systemd_ts(value: str) -> str | None:
    """`--timestamp=unix` → `@1697012345`; eski systemd matn qaytaradi."""
    if not value or value == "n/a":
        return None
    if value.startswith("@"):
        try:
            return _ts(float(value[1:]))
        except ValueError:
            return None
    return value


def collect_services() -> dict:
    units = configured_units()
    if not shutil.which("systemctl"):
        return {"available": False, "units": []}

    base = ["systemctl", "show", "--no-pager", f"--property={_UNIT_PROPS}"]
    proc = subprocess.run(
        [*base, "--timestamp=unix", *units], capture_output=True, text=True, timeout=5
    )
    if proc.returncode != 0 and "timestamp" in (proc.stderr or ""):
        # systemd < 248 — `--timestamp` yo'q.
        proc = subprocess.run([*base, *units], capture_output=True, text=True, timeout=5)

    blocks = [b for b in proc.stdout.strip().split("\n\n") if b.strip()]
    result = []
    for unit, block in zip(units, blocks):
        props = dict(line.split("=", 1) for line in block.splitlines() if "=" in line)
        mem_raw = props.get("MemoryCurrent", "")
        memory = int(mem_raw) if mem_raw.isdigit() and int(mem_raw) < 2**63 else None
        result.append(
            {
                "unit": props.get("Id") or unit,
                "description": props.get("Description", ""),
                "load_state": props.get("LoadState", ""),
                "active_state": props.get("ActiveState", ""),
                "sub_state": props.get("SubState", ""),
                "enabled": props.get("UnitFileState", ""),
                "main_pid": int(props.get("MainPID") or 0),
                "since": _parse_systemd_ts(props.get("ActiveEnterTimestamp", "")),
                "restarts": int(props["NRestarts"]) if props.get("NRestarts", "").isdigit() else None,
                "memory": memory,
            }
        )
    return {"available": True, "units": result}


# ============================================================================
# PostgreSQL
# ============================================================================


def _session() -> Session:
    from app.db.session import SessionLocal

    return SessionLocal()


def _limit_statement(db: Session) -> None:
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text(f"SET LOCAL statement_timeout = '{_DB_STATEMENT_TIMEOUT}'"))


def collect_database() -> dict:
    from app.db.session import engine

    pool = engine.pool
    pool_info = (
        {
            "size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "max_overflow": settings.DB_MAX_OVERFLOW,
        }
        if isinstance(pool, QueuePool)
        else None
    )

    with _session() as db:
        t0 = time.perf_counter()
        db.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        data: dict[str, Any] = {
            "dialect": db.get_bind().dialect.name,
            "latency_ms": latency_ms,
            # Pool — shu gunicorn worker'niki (har worker o'z pooliga ega).
            "pool": pool_info,
        }
        if data["dialect"] != "postgresql":
            return data

        _limit_statement(db)
        q = lambda sql: db.execute(text(sql))  # noqa: E731
        data["version"] = q("SHOW server_version").scalar()
        data["size_bytes"] = q("SELECT pg_database_size(current_database())").scalar()
        data["max_connections"] = int(q("SHOW max_connections").scalar())
        data["connections_total"] = q("SELECT count(*) FROM pg_stat_activity").scalar()
        data["connections_by_state"] = {
            (row[0] or "background"): row[1]
            for row in q(
                "SELECT state, count(*) FROM pg_stat_activity "
                "WHERE datname = current_database() GROUP BY state"
            )
        }
        data["waiting_locks"] = q("SELECT count(*) FROM pg_locks WHERE NOT granted").scalar()
        st = q(
            "SELECT xact_commit, xact_rollback, blks_hit, blks_read, deadlocks, "
            "temp_bytes, conflicts FROM pg_stat_database WHERE datname = current_database()"
        ).mappings().first()
        if st:
            hits, reads = st["blks_hit"] or 0, st["blks_read"] or 0
            data["stats"] = {
                "commits": st["xact_commit"],
                "rollbacks": st["xact_rollback"],
                "deadlocks": st["deadlocks"],
                "temp_bytes": st["temp_bytes"],
                "conflicts": st["conflicts"],
                "cache_hit_percent": round(hits * 100 / (hits + reads), 2) if hits + reads else None,
            }
        data["long_queries"] = [
            {
                "pid": r["pid"],
                "duration_seconds": round(r["duration"] or 0, 1),
                "state": r["state"],
                "wait": ":".join(x for x in (r["wait_event_type"], r["wait_event"]) if x) or None,
                "application": r["application_name"] or None,
                "query": r["query"],
            }
            for r in q(
                "SELECT pid, EXTRACT(EPOCH FROM now() - query_start) AS duration, state, "
                "wait_event_type, wait_event, application_name, left(query, 400) AS query "
                "FROM pg_stat_activity WHERE datname = current_database() "
                "AND state IS NOT NULL AND state <> 'idle' AND pid <> pg_backend_pid() "
                "AND query_start < now() - interval '5 seconds' "
                "ORDER BY query_start LIMIT 10"
            ).mappings()
        ]
        data["tables"] = [
            {
                "name": r["relname"],
                "rows": r["n_live_tup"],
                "dead_rows": r["n_dead_tup"],
                "size_bytes": r["size"],
                "last_autovacuum": r["last_autovacuum"].isoformat() if r["last_autovacuum"] else None,
            }
            for r in q(
                "SELECT relname, n_live_tup, n_dead_tup, pg_total_relation_size(relid) AS size, "
                "last_autovacuum FROM pg_stat_user_tables "
                "ORDER BY pg_total_relation_size(relid) DESC LIMIT 10"
            ).mappings()
        ]
        db.rollback()
        return data


# ============================================================================
# Redis va Celery
# ============================================================================

_CELERY_QUEUES = ("verify", "storage")


def collect_redis() -> dict:
    from app.core.redis_client import get_redis

    r = get_redis()
    t0 = time.perf_counter()
    r.ping()
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    info = r.info()
    pipe = r.pipeline()
    for q in _CELERY_QUEUES:
        pipe.llen(q)
    pipe.hlen("unacked")
    pipe.dbsize()
    *lens, unacked, dbsize = pipe.execute()
    hits = info.get("keyspace_hits", 0)
    misses = info.get("keyspace_misses", 0)
    return {
        "latency_ms": latency_ms,
        "version": info.get("redis_version"),
        "uptime_seconds": info.get("uptime_in_seconds"),
        "used_memory": info.get("used_memory"),
        "used_memory_peak": info.get("used_memory_peak"),
        "maxmemory": info.get("maxmemory") or None,
        "connected_clients": info.get("connected_clients"),
        "blocked_clients": info.get("blocked_clients"),
        "ops_per_sec": info.get("instantaneous_ops_per_sec"),
        "hit_percent": round(hits * 100 / (hits + misses), 2) if hits + misses else None,
        "evicted_keys": info.get("evicted_keys"),
        "rejected_connections": info.get("rejected_connections"),
        "keys": dbsize,
        "queues": {q: n for q, n in zip(_CELERY_QUEUES, lens)},
        # Workerga berilgan, lekin hali tasdiqlanmagan (bajarilayotgan) tasklar.
        "unacked": unacked,
        "queue_limit": settings.QUEUE_MAX_SIZE,
    }


def collect_celery() -> dict:
    """Ishlayotgan workerlar, ularning pooli va hozir bajarilayotgan tasklar.

    Task argumentlari qaytarilmaydi (rasm/JShShIR bo'lishi mumkin) — faqat nomi
    va qancha vaqtdan beri ishlayotgani.
    """
    from app.celery_app import celery_app

    def inspect(method: str) -> dict:
        insp = celery_app.control.inspect(timeout=_CELERY_INSPECT_TIMEOUT)
        return getattr(insp, method)() or {}

    # Har chaqiruv javob kutib timeout'gacha turadi — uchalasi parallel.
    with ThreadPoolExecutor(max_workers=3) as ex:
        stats_f, active_f, queues_f = (
            ex.submit(inspect, m) for m in ("stats", "active", "active_queues")
        )
        stats, active, queues = stats_f.result(), active_f.result(), queues_f.result()

    now = time.time()
    workers = []
    for host in sorted(set(stats) | set(active) | set(queues)):
        st = stats.get(host) or {}
        pool = st.get("pool") or {}
        tasks = active.get(host) or []
        workers.append(
            {
                "hostname": host,
                "pid": st.get("pid"),
                "uptime_seconds": st.get("uptime"),
                "pool": pool.get("implementation", "").rsplit(":", 1)[-1] or None,
                "concurrency": pool.get("max-concurrency"),
                "queues": sorted(q.get("name", "") for q in queues.get(host) or []),
                "processed": sum((st.get("total") or {}).values()),
                "processed_by_task": st.get("total") or {},
                "active": [
                    {
                        "name": t.get("name"),
                        "running_seconds": round(now - t["time_start"], 1)
                        if t.get("time_start")
                        else None,
                    }
                    for t in tasks
                ],
            }
        )
    return {"workers": workers}


# ============================================================================
# Ilova va faollik
# ============================================================================


def collect_app() -> dict:
    from app.services import face_service

    proc = psutil.Process()
    return {
        "name": settings.APP_NAME,
        "pid": proc.pid,
        "worker_started_at": _ts(proc.create_time()),
        # Model har jarayonda alohida yuklanadi — bu shu API worker'niki.
        "face_model_ready": face_service._face_app_ready.is_set(),
        "queue_max_size": settings.QUEUE_MAX_SIZE,
        "embedding_workers": settings.EMBEDDING_WORKERS,
    }


def _count(db: Session, stmt) -> int | None:
    try:
        with db.begin_nested():
            return db.execute(stmt).scalar() or 0
    except Exception as exc:  # noqa: BLE001 — bitta sanoq yiqilsa qolganlari ko'rinsin
        logger.warning("Monitoring sanog'i xatosi: %s", exc)
        return None


def collect_activity() -> dict:
    """Tizim yuklamasi — oxirgi daqiqalardagi Face ID va tekshiruvlar soni.

    Natija Redis'da `_ACTIVITY_CACHE_TTL` soniya keshlanadi.
    """
    from app.core.redis_client import get_redis

    try:
        cached = get_redis().get(_ACTIVITY_CACHE_KEY)
        if cached:
            return json.loads(cached)
    except Exception:  # noqa: BLE001
        pass

    from app.api.v1.endpoints.online_users import ONLINE_WINDOW_MINUTES
    from app.models.failed_login_attempt import FailedLoginAttempt
    from app.models.refresh_token import RefreshToken
    from app.models.session_state import SessionState
    from app.models.student_log import StudentLog
    from app.models.test_session import TestSession
    from app.models.verification_log import VerificationLog

    now = _now()
    m15, h1, d1 = now - timedelta(minutes=15), now - timedelta(hours=1), now - timedelta(days=1)
    with _session() as db:
        _limit_statement(db)
        data = {
            "face_id_15m": _count(
                db, select(func.count()).select_from(StudentLog).where(StudentLog.last_enter_time >= m15)
            ),
            "face_id_1h": _count(
                db, select(func.count()).select_from(StudentLog).where(StudentLog.last_enter_time >= h1)
            ),
            "verify_15m": _count(
                db, select(func.count()).select_from(VerificationLog).where(VerificationLog.timestamp >= m15)
            ),
            "verify_1h": _count(
                db, select(func.count()).select_from(VerificationLog).where(VerificationLog.timestamp >= h1)
            ),
            "verify_24h": _count(
                db, select(func.count()).select_from(VerificationLog).where(VerificationLog.timestamp >= d1)
            ),
            "failed_logins_1h": _count(
                db,
                select(func.count())
                .select_from(FailedLoginAttempt)
                .where(FailedLoginAttempt.attempted_at >= h1),
            ),
            "online_users": _count(
                db,
                select(func.count(func.distinct(RefreshToken.user_id))).where(
                    RefreshToken.revoked.is_(False),
                    RefreshToken.expires_at > now,
                    RefreshToken.created_at >= now - timedelta(minutes=ONLINE_WINDOW_MINUTES),
                ),
            ),
            "active_sessions": _count(
                db,
                select(func.count())
                .select_from(TestSession)
                .join(SessionState, SessionState.id == TestSession.test_state_id)
                .where(SessionState.key == 4),
            ),
            "computed_at": now.isoformat(),
        }
        db.rollback()

    try:
        get_redis().setex(_ACTIVITY_CACHE_KEY, _ACTIVITY_CACHE_TTL, json.dumps(data))
    except Exception:  # noqa: BLE001
        pass
    return data


# ============================================================================
# Ogohlantirishlar va umumiy ko'rinish
# ============================================================================


def _alert(level: str, source: str, message: str) -> dict:
    return {"level": level, "source": source, "message": message}


def _pct_alert(alerts: list, value: float | None, source: str, label: str) -> None:
    if value is None:
        return
    if value >= _CRIT_PCT:
        alerts.append(_alert("critical", source, f"{label} {value:.0f}% — juda yuqori"))
    elif value >= _WARN_PCT:
        alerts.append(_alert("warning", source, f"{label} {value:.0f}% — yuqori"))


def build_alerts(data: dict) -> list[dict]:
    alerts: list[dict] = []
    system = data.get("system") or {}
    if system.get("ok"):
        cpu, mem = system["cpu"], system["memory"]
        _pct_alert(alerts, cpu["percent"], "cpu", "CPU yuklamasi")
        _pct_alert(alerts, mem["percent"], "memory", "RAM band")
        if mem["swap_total"] and mem["swap_percent"] >= 50:
            alerts.append(
                _alert("warning", "memory", f"Swap {mem['swap_percent']:.0f}% band — RAM yetmayapti")
            )
        if cpu["cores_logical"] and cpu["load_5"] > cpu["cores_logical"] * 1.5:
            alerts.append(
                _alert(
                    "warning",
                    "cpu",
                    f"Load average (5 daq) {cpu['load_5']} — yadrolar sonidan "
                    f"({cpu['cores_logical']}) ancha ko'p",
                )
            )
        for d in system["disks"]:
            _pct_alert(alerts, d["percent"], "disk", f"Disk {d['mountpoint']}")

    services = data.get("services") or {}
    for u in services.get("units") or []:
        if u["load_state"] == "not-found":
            continue
        if u["active_state"] == "failed":
            alerts.append(_alert("critical", "service", f"{u['unit']} — ishdan chiqqan (failed)"))
        elif u["active_state"] != "active":
            alerts.append(_alert("critical", "service", f"{u['unit']} — ishlamayapti ({u['active_state']})"))

    db = data.get("database") or {}
    if not db.get("ok"):
        alerts.append(_alert("critical", "database", "PostgreSQL bilan aloqa yo'q"))
    else:
        if db.get("max_connections") and db.get("connections_total"):
            _pct_alert(
                alerts,
                db["connections_total"] * 100 / db["max_connections"],
                "database",
                "PostgreSQL ulanishlari",
            )
        long_q = [q for q in db.get("long_queries") or [] if q["duration_seconds"] >= 30]
        if long_q:
            alerts.append(_alert("warning", "database", f"{len(long_q)} ta so'rov 30 s dan uzoq ishlayapti"))
        if db.get("waiting_locks"):
            alerts.append(_alert("warning", "database", f"{db['waiting_locks']} ta qulf kutilmoqda"))

    redis = data.get("redis") or {}
    if not redis.get("ok"):
        alerts.append(_alert("critical", "redis", "Redis bilan aloqa yo'q — Celery va login ishlamaydi"))
    else:
        limit = redis.get("queue_limit") or 0
        verify_len = (redis.get("queues") or {}).get("verify", 0)
        if limit and verify_len >= limit:
            alerts.append(
                _alert("critical", "celery", f"verify navbati to'la ({verify_len}/{limit}) — so'rovlar 429 olmoqda")
            )
        elif limit and verify_len >= limit * 0.7:
            alerts.append(_alert("warning", "celery", f"verify navbati to'lmoqda ({verify_len}/{limit})"))

    celery = data.get("celery") or {}
    if celery.get("ok"):
        served = {q for w in celery["workers"] for q in w["queues"]}
        if not celery["workers"]:
            alerts.append(_alert("critical", "celery", "Birorta Celery worker javob bermadi"))
        else:
            for q in _CELERY_QUEUES:
                if q not in served:
                    alerts.append(_alert("warning", "celery", f"'{q}' navbati uchun worker topilmadi"))

    history = data.get("history_last_sample")
    if history is None:
        alerts.append(
            _alert("info", "history", "Yuklama tarixi yozilmayapti — Celery beat/storage worker ishlayaptimi?")
        )
    elif (_now() - datetime.fromisoformat(history)).total_seconds() > SAMPLE_INTERVAL_SECONDS * 3:
        alerts.append(_alert("warning", "history", "Yuklama tarixi 3 daqiqadan beri yangilanmagan (Celery beat?)"))

    order = {"critical": 0, "warning": 1, "info": 2}
    return sorted(alerts, key=lambda a: order[a["level"]])


def _last_sample_time() -> str | None:
    from app.core.redis_client import get_redis

    try:
        raw = get_redis().lindex(HISTORY_KEY, 0)
    except Exception:  # noqa: BLE001
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)["t"]
    except (ValueError, KeyError):
        return None


def collect_overview() -> dict:
    """Barcha bo'limlar parallel yig'iladi — eng sekini (Celery inspect ~1 s) belgilaydi."""
    sections: dict[str, Callable[[], dict]] = {
        "system": collect_system,
        "services": collect_services,
        "database": collect_database,
        "redis": collect_redis,
        "celery": collect_celery,
        "app": collect_app,
        "activity": collect_activity,
    }
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=len(sections)) as ex:
        futures = {k: ex.submit(_safe, fn) for k, fn in sections.items()}
        data: dict[str, Any] = {k: f.result() for k, f in futures.items()}
    data["history_last_sample"] = _last_sample_time()
    data["alerts"] = build_alerts(data)
    data["generated_at"] = _now().isoformat()
    data["collect_ms"] = round((time.perf_counter() - started) * 1000)
    return data


# ============================================================================
# Yuklama tarixi (Celery beat → Redis)
# ============================================================================


def take_sample() -> dict:
    """Bitta tarix nuqtasi. Tarmoq/disk — kumulyativ sanoq, tezlik o'qishda hisoblanadi."""
    cpu = psutil.cpu_percent(interval=1.0)
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    net = psutil.net_io_counters()
    dio = psutil.disk_io_counters()
    try:
        load1 = psutil.getloadavg()[0]
    except (AttributeError, OSError):
        load1 = 0.0
    try:
        disk_pct = psutil.disk_usage(str(BACKEND_DIR)).percent
    except OSError:
        disk_pct = None
    sample: dict[str, Any] = {
        "t": _now().isoformat(),
        "cpu": round(cpu, 1),
        "mem": round(vm.percent, 1),
        "swap": round(sw.percent, 1),
        "load1": round(load1, 2),
        "disk": disk_pct,
        "net_tx": net.bytes_sent if net else None,
        "net_rx": net.bytes_recv if net else None,
        "disk_r": dio.read_bytes if dio else None,
        "disk_w": dio.write_bytes if dio else None,
    }
    try:
        from app.core.redis_client import get_redis

        r = get_redis()
        sample["q_verify"] = r.llen("verify")
        sample["q_storage"] = r.llen("storage")
    except Exception:  # noqa: BLE001
        pass
    try:
        with _session() as db:
            if db.get_bind().dialect.name == "postgresql":
                _limit_statement(db)
                sample["db_conn"] = db.execute(text("SELECT count(*) FROM pg_stat_activity")).scalar()
    except Exception:  # noqa: BLE001
        pass
    return sample


def record_sample() -> dict:
    from app.core.redis_client import get_redis

    sample = take_sample()
    r = get_redis()
    pipe = r.pipeline()
    pipe.lpush(HISTORY_KEY, json.dumps(sample))
    pipe.ltrim(HISTORY_KEY, 0, HISTORY_MAX - 1)
    pipe.execute()
    return sample


def _per_sec(prev: dict, cur: dict, key: str, dt: float) -> float | None:
    a, b = prev.get(key), cur.get(key)
    if a is None or b is None or dt <= 0 or b < a:  # b < a — server qayta yuklangan
        return None
    return round((b - a) / dt, 1)


def read_history(minutes: int) -> list[dict]:
    """Eskidan yangiga tartiblangan nuqtalar, tarmoq/disk tezligi bilan (bayt/s)."""
    from app.core.redis_client import get_redis

    raw = get_redis().lrange(HISTORY_KEY, 0, max(1, minutes))
    samples = []
    for item in reversed(raw):
        try:
            samples.append(json.loads(item))
        except ValueError:
            continue
    cutoff = _now() - timedelta(minutes=minutes)
    out = []
    prev = None
    for s in samples:
        t = datetime.fromisoformat(s["t"])
        point = {
            "t": s["t"],
            "cpu": s.get("cpu"),
            "mem": s.get("mem"),
            "swap": s.get("swap"),
            "load1": s.get("load1"),
            "disk": s.get("disk"),
            "q_verify": s.get("q_verify"),
            "q_storage": s.get("q_storage"),
            "db_conn": s.get("db_conn"),
            "net_tx": None,
            "net_rx": None,
            "disk_r": None,
            "disk_w": None,
        }
        if prev is not None:
            dt = (t - datetime.fromisoformat(prev["t"])).total_seconds()
            # Oraliq juda katta bo'lsa (beat to'xtagan) — tezlik ma'nosiz.
            if dt <= SAMPLE_INTERVAL_SECONDS * 3:
                for k in ("net_tx", "net_rx", "disk_r", "disk_w"):
                    point[k] = _per_sec(prev, s, k, dt)
        prev = s
        # Oldingi nuqta tezlik uchun kerak, lekin oynadan tashqaridagi nuqta qaytmaydi.
        if t >= cutoff:
            out.append(point)
    return out


# ============================================================================
# Loglar
# ============================================================================

_LOG_EXCLUDED_SUFFIXES = (".gz", ".xz", ".bz2", ".zip", ".zst")
_MAX_LOG_FILES = 200
_MAX_LINE_CHARS = 4000
_TAIL_CHUNK = 64 * 1024
TAIL_MAX_SCAN_BYTES = 32 * 1024 * 1024

# Loglarda uchraydigan maxfiy qiymatlar — javobga chiqishdan oldin yashiriladi.
_REDACTIONS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"/bot\d+:[A-Za-z0-9_-]+"), "/bot***"),
    (re.compile(r"(?i)\b(authorization\s*[:=]\s*[\"']?(?:bearer|tma|basic)\s+)[^\s\"',]+"), r"\1***"),
    (
        re.compile(
            r"(?i)\b(x-api-key|api[_-]?key|access_token|refresh_token|token|password|passwd|secret)"
            r"([\"']?\s*[:=]\s*[\"']?)[^\s\"'&,;}]+"
        ),
        r"\1\2***",
    ),
    (re.compile(r"(?i)(postgres(?:ql)?(?:\+\w+)?://[^:/\s]+:)[^@\s]+@"), r"\1***@"),
    (re.compile(r"(?i)(redis://[^:/\s]*:)[^@\s]+@"), r"\1***@"),
)


def redact(line: str) -> str:
    for pattern, repl in _REDACTIONS:
        line = pattern.sub(repl, line)
    return line


def _log_dirs() -> list[tuple[str, Path]]:
    """(yorliq, papka). Yorliq — `backend`, `davomat_bot`, `nginx` kabi."""
    out: list[tuple[str, Path]] = []
    labels: set[str] = set()
    for raw in settings.MONITOR_LOG_DIRS.split(","):
        raw = raw.strip()
        if not raw:
            continue
        path = Path(raw)
        if not path.is_absolute():
            path = BACKEND_DIR / path
        path = path.resolve()
        label = path.parent.name if path.name == "logs" else path.name
        label = label or "logs"
        base, n = label, 2
        while label in labels:
            label = f"{base}{n}"
            n += 1
        labels.add(label)
        out.append((label, path))
    return out


def _iter_log_files() -> Iterator[tuple[str, Path, os.stat_result]]:
    count = 0
    for label, directory in _log_dirs():
        try:
            entries = sorted(directory.iterdir(), key=lambda p: p.name)
        except OSError:
            continue
        for path in entries:
            if ".log" not in path.name or path.name.endswith(_LOG_EXCLUDED_SUFFIXES):
                continue
            try:
                st = path.stat()
            except OSError:
                continue
            if not path.is_file():
                continue
            yield f"{label}/{path.name}", path, st
            count += 1
            if count >= _MAX_LOG_FILES:
                return


def list_log_files() -> list[dict]:
    return [
        {
            "key": key,
            "group": key.split("/", 1)[0],
            "name": path.name,
            "size": st.st_size,
            "modified_at": _ts(st.st_mtime),
            "readable": os.access(path, os.R_OK),
        }
        for key, path, st in _iter_log_files()
    ]


def resolve_log_file(key: str) -> Path | None:
    """Kalit faqat ro'yxatdagi faylga mos kelsa — yo'l kiritib bo'lmaydi (path traversal yo'q)."""
    for k, path, _ in _iter_log_files():
        if k == key:
            return path
    return None


_LEVEL_PATTERNS = {
    "error": re.compile(r"\b(ERROR|CRITICAL|FATAL|PANIC)\b|\[(error|crit|alert|emerg)\]|Traceback"),
    "warning": re.compile(
        r"\b(WARNING|WARN|ERROR|CRITICAL|FATAL|PANIC)\b|\[(warn|error|crit|alert|emerg)\]|Traceback"
    ),
}


def make_line_filter(query: str | None, level: str | None) -> Callable[[str], bool]:
    q = (query or "").lower()
    level_re = _LEVEL_PATTERNS.get(level or "")

    def match(line: str) -> bool:
        if q and q not in line.lower():
            return False
        if level_re is not None and not level_re.search(line):
            return False
        return True

    return match


def tail_file(
    path: Path,
    lines: int,
    query: str | None = None,
    level: str | None = None,
    max_scan_bytes: int = TAIL_MAX_SCAN_BYTES,
) -> dict:
    """Faylning oxiridan `lines` ta (filtrga mos) qatorni o'qiydi.

    Fayl boshidan emas, oxiridan bo'laklab o'qiladi — gigabaytli access.log
    ham tez ochiladi. Filtr bilan ko'pi bilan `max_scan_bytes` ko'riladi.
    """
    match = make_line_filter(query, level)
    found: list[str] = []
    scanned = 0
    with path.open("rb") as f:
        f.seek(0, os.SEEK_END)
        size = pos = f.tell()
        rest = b""
        while pos > 0 and len(found) < lines and scanned < max_scan_bytes:
            step = min(_TAIL_CHUNK, pos)
            pos -= step
            f.seek(pos)
            buf = f.read(step) + rest
            scanned += step
            parts = buf.split(b"\n")
            # Birinchi bo'lak — oldingi qatorning davomi bo'lishi mumkin (fayl boshi bo'lmasa).
            rest = parts.pop(0) if pos > 0 else b""
            for raw in reversed(parts):
                if _collect_line(raw, match, found) and len(found) >= lines:
                    break
        if pos == 0 and rest and len(found) < lines:
            _collect_line(rest, match, found)
    found.reverse()
    st = path.stat()
    return {
        "size": size,
        "modified_at": _ts(st.st_mtime),
        "scanned_bytes": min(scanned, size),
        # Fayl to'liq ko'rilmadi va so'ralganicha qator topilmadi.
        "scan_limited": pos > 0 and len(found) < lines,
        "lines": found,
    }


def _collect_line(raw: bytes, match: Callable[[str], bool], found: list[str]) -> bool:
    line = raw.decode("utf-8", errors="replace").rstrip("\r")
    if not line.strip() or not match(line):
        return False
    if len(line) > _MAX_LINE_CHARS:
        line = line[:_MAX_LINE_CHARS] + " …"
    found.append(redact(line))
    return True


def iter_redacted_file(path: Path) -> Iterator[bytes]:
    """Faylni to'liq yuklab olish uchun — har qator maxfiy qiymatlardan tozalanadi."""
    with path.open("rb") as f:
        for raw in f:
            yield redact(raw.decode("utf-8", errors="replace")).encode("utf-8")


def journal_tail(unit: str, lines: int, query: str | None, level: str | None) -> dict:
    """`journalctl -u <unit>` oxirgi qatorlari. Unit faqat sozlamadagi ro'yxatdan."""
    if not shutil.which("journalctl"):
        return {"available": False, "lines": []}
    # Filtr bilan ko'proq o'qib, keyin saralaymiz (journalctl -g har serverda yo'q).
    fetch = lines if not (query or level) else min(lines * 20, 20000)
    proc = subprocess.run(
        ["journalctl", "-u", unit, "-n", str(fetch), "--no-pager", "-o", "short-iso", "-q"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    match = make_line_filter(query, level)
    out = [redact(line) for line in proc.stdout.splitlines() if line.strip() and match(line)]
    return {
        "available": True,
        "lines": out[-lines:],
        # Bo'sh natija va stderr — ko'pincha huquq yo'qligi (systemd-journal guruhi).
        "error": (proc.stderr or "").strip()[:500] or None,
    }
