"""Server monitoringi servisining sof qismlari: log o'qish, yashirish, tarix, ogohlantirishlar."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from app.config import settings
from app.models.role import Role
from app.models.user import User
from app.services import server_monitor as mon


# --- superadmin ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("user_id", "role_key", "expected"),
    [(1, 1, True), (2, 1, False), (1, 5, False)],
)
def test_is_super_admin(user_id, role_key, expected):
    user = User(id=user_id, username="u", role_ref=Role(key=role_key, name="r"))
    assert user.is_super_admin is expected


def test_user_without_role_is_not_super_admin():
    assert User(id=1, username="u").is_super_admin is False


# --- jarayonlarni guruhlash ----------------------------------------------------


@pytest.mark.parametrize(
    ("name", "cmd", "group"),
    [
        ("python", ["venv/bin/celery", "-A", "app.celery_app", "worker", "-Q", "verify"], "celery_verify"),
        ("python", ["celery", "-A", "app.celery_app", "worker", "--queues=storage"], "celery_storage"),
        ("python", ["celery", "-A", "app.celery_app", "beat"], "celery_beat"),
        ("python", ["celery", "worker"], "celery_other"),
        ("python", ["gunicorn", "app.main:app", "-c", "gunicorn_config.py"], "api"),
        ("python", ["/var/www/faceid_davomat/davomat_bot/venv/bin/python", "main.py"], "davomat_bot"),
        ("python", ["/var/www/faceid_davomat/statistic_bot/venv/bin/python", "bot.py"], "statistic_bot"),
        ("postgres", [], "postgres"),
        ("redis-server", [], "redis"),
        ("nginx", ["nginx: worker process"], "nginx"),
        ("sshd", ["sshd"], None),
    ],
)
def test_classify_process(name, cmd, group):
    assert mon.classify_process(name, cmd) == group


# --- maxfiy qiymatlarni yashirish ----------------------------------------------


@pytest.mark.parametrize(
    ("line", "secret"),
    [
        ("POST https://api.telegram.org/bot123456:AAH-abc_def/sendMessage", "AAH-abc_def"),
        ("Authorization: Bearer eyJhbGciOi.payload.sig", "eyJhbGciOi"),
        ("headers={'X-API-Key': 'sk-live-123'}", "sk-live-123"),
        ("GET /x?token=abc123&page=2", "abc123"),
        ('{"password": "hunter2"}', "hunter2"),
        ("postgresql://postgres:4144@localhost:5432/faceid_db", "4144"),
        ("redis://:s3cret@127.0.0.1:6379/0", "s3cret"),
    ],
)
def test_redact_hides_secrets(line, secret):
    out = mon.redact(line)
    assert secret not in out
    assert "***" in out


def test_redact_keeps_normal_lines():
    line = "2026-10-21 10:00:00 | INFO | faceid | GET /api/v1/students -> 200 12.3ms"
    assert mon.redact(line) == line


# --- log fayllari --------------------------------------------------------------


@pytest.fixture
def log_dirs(tmp_path, monkeypatch):
    backend_logs = tmp_path / "backend" / "logs"
    bot_logs = tmp_path / "davomat_bot" / "logs"
    backend_logs.mkdir(parents=True)
    bot_logs.mkdir(parents=True)
    (backend_logs / "error.log").write_text("a\nb\n", encoding="utf-8")
    (backend_logs / "access.log.1").write_text("old\n", encoding="utf-8")
    (backend_logs / "access.log.2.gz").write_bytes(b"\x1f\x8b")
    (backend_logs / "notes.txt").write_text("x", encoding="utf-8")
    (bot_logs / "bot.log").write_text("bot\n", encoding="utf-8")
    (tmp_path / "secret.log").write_text("SECRET", encoding="utf-8")
    monkeypatch.setattr(
        settings, "MONITOR_LOG_DIRS", f"{backend_logs},{bot_logs},{tmp_path / 'missing'}"
    )
    return tmp_path


def test_list_log_files(log_dirs):
    keys = [f["key"] for f in mon.list_log_files()]
    assert keys == ["backend/access.log.1", "backend/error.log", "davomat_bot/bot.log"]


@pytest.mark.parametrize(
    "key",
    ["backend/../../secret.log", "../secret.log", "backend/notes.txt", "backend/access.log.2.gz", "/etc/passwd"],
)
def test_resolve_log_file_rejects_unlisted(log_dirs, key):
    assert mon.resolve_log_file(key) is None


def test_resolve_log_file(log_dirs):
    assert mon.resolve_log_file("davomat_bot/bot.log") == log_dirs / "davomat_bot" / "logs" / "bot.log"


# --- tail ----------------------------------------------------------------------


def _write(tmp_path, lines, newline="\n", trailing=True):
    path = tmp_path / "app.log"
    body = newline.join(lines) + (newline if trailing else "")
    path.write_bytes(body.encode("utf-8"))
    return path


@pytest.mark.parametrize("chunk", [7, 64, 64 * 1024])
@pytest.mark.parametrize("trailing", [True, False])
def test_tail_returns_last_lines_in_order(tmp_path, monkeypatch, chunk, trailing):
    monkeypatch.setattr(mon, "_TAIL_CHUNK", chunk)
    lines = [f"line {i:03d} " + "x" * (i % 13) for i in range(200)]
    path = _write(tmp_path, lines, trailing=trailing)

    res = mon.tail_file(path, 25)
    assert res["lines"] == lines[-25:]
    assert res["scan_limited"] is False

    # Butun fayldan ko'p so'ralsa — hammasi, birinchi qator ham yo'qolmaydi.
    assert mon.tail_file(path, 1000)["lines"] == lines


def test_tail_crlf_and_blank_lines(tmp_path):
    path = _write(tmp_path, ["a", "", "b", "  ", "c"], newline="\r\n")
    assert mon.tail_file(path, 10)["lines"] == ["a", "b", "c"]


def test_tail_filters(tmp_path, monkeypatch):
    monkeypatch.setattr(mon, "_TAIL_CHUNK", 16)
    lines = [
        "2026-10-21 | INFO | GET /students -> 200",
        "2026-10-21 | WARNING | slow query",
        "2026-10-21 | ERROR | boom",
        "Traceback (most recent call last):",
        "[2026-10-21 10:00:00 +0500] [123] [ERROR] Worker timeout",
        "2026-10-21 | INFO | GET /students -> 500",
    ]
    path = _write(tmp_path, lines)
    assert mon.tail_file(path, 10, level="error")["lines"] == [lines[2], lines[3], lines[4]]
    assert mon.tail_file(path, 10, level="warning")["lines"] == lines[1:5]
    assert mon.tail_file(path, 10, query="STUDENTS")["lines"] == [lines[0], lines[5]]
    assert mon.tail_file(path, 1, query="students")["lines"] == [lines[5]]


def test_tail_scan_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(mon, "_TAIL_CHUNK", 100)
    path = _write(tmp_path, ["ERROR first"] + ["info"] * 500)
    res = mon.tail_file(path, 10, level="error", max_scan_bytes=300)
    assert res["lines"] == []
    assert res["scan_limited"] is True


def test_tail_truncates_and_redacts(tmp_path):
    path = _write(tmp_path, ["token=abc " + "y" * 10000])
    (line,) = mon.tail_file(path, 5)["lines"]
    assert "abc" not in line
    assert line.endswith(" …")
    assert len(line) < 4100


def test_iter_redacted_file(tmp_path):
    path = _write(tmp_path, ["ok", "password=hunter2"])
    body = b"".join(mon.iter_redacted_file(path)).decode()
    assert body == "ok\npassword=***\n"


# --- tarix ---------------------------------------------------------------------


class _FakeRedis:
    def __init__(self, items):
        self.items = items  # yangisi birinchi (LPUSH tartibi)

    def lrange(self, key, start, end):
        return self.items[start : end + 1]


def test_read_history_rates_and_window(monkeypatch):
    now = datetime.now(timezone.utc)

    def sample(min_ago, tx, **kw):
        return {"t": (now - timedelta(minutes=min_ago)).isoformat(), "cpu": 10, "net_tx": tx,
                "net_rx": 0, "disk_r": 0, "disk_w": 0, **kw}

    oldest_first = [
        sample(12, 0),        # oynadan tashqarida — faqat tezlik uchun
        sample(9, 6000),      # 3 daqiqalik bo'shliq: 180 s — chegarada, tezlik hisoblanadi
        sample(8, 12000),
        sample(1, 99999),     # 7 daqiqalik bo'shliq — tezlik yo'q
        sample(0, 50),        # hisoblagich qaytgan (server qayta yuklangan)
    ]
    fake = _FakeRedis([json.dumps(s) for s in reversed(oldest_first)])
    monkeypatch.setattr("app.core.redis_client.get_redis", lambda: fake)

    points = mon.read_history(10)
    assert len(points) == 4
    assert [p["net_tx"] for p in points] == [pytest.approx(6000 / 180, abs=0.1), 100.0, None, None]
    assert points[0]["cpu"] == 10


# --- ogohlantirishlar ----------------------------------------------------------


def _healthy():
    return {
        "system": {
            "ok": True,
            "cpu": {"percent": 20, "load_5": 1, "cores_logical": 8},
            "memory": {"percent": 40, "swap_total": 1, "swap_percent": 0},
            "disks": [{"mountpoint": "/", "percent": 50}],
        },
        "services": {"units": [{"unit": "faceid-api.service", "load_state": "loaded", "active_state": "active"}]},
        "database": {"ok": True, "max_connections": 100, "connections_total": 10, "long_queries": [], "waiting_locks": 0},
        "redis": {"ok": True, "queue_limit": 100, "queues": {"verify": 0}},
        "celery": {"ok": True, "workers": [{"hostname": "a", "queues": ["verify", "storage"]}]},
        "history_last_sample": datetime.now(timezone.utc).isoformat(),
    }


def test_alerts_healthy():
    assert mon.build_alerts(_healthy()) == []


def test_alerts_problems_sorted_by_severity():
    data = _healthy()
    data["system"]["memory"]["percent"] = 90
    data["system"]["disks"][0]["percent"] = 97
    data["services"]["units"] += [
        {"unit": "faceid-celery-beat.service", "load_state": "loaded", "active_state": "failed"},
        {"unit": "statistic.service", "load_state": "not-found", "active_state": "inactive"},
    ]
    data["redis"]["queues"]["verify"] = 100
    data["celery"]["workers"][0]["queues"] = ["verify"]
    data["history_last_sample"] = None

    alerts = mon.build_alerts(data)
    levels = [a["level"] for a in alerts]
    assert levels == sorted(levels, key=["critical", "warning", "info"].index)
    sources = {(a["level"], a["source"]) for a in alerts}
    assert ("critical", "disk") in sources
    assert ("warning", "memory") in sources
    assert ("critical", "service") in sources
    assert ("critical", "celery") in sources  # navbat to'la
    assert ("warning", "celery") in sources  # storage uchun worker yo'q
    assert ("info", "history") in sources
    # O'rnatilmagan unit ogohlantirish bermaydi.
    assert not any("statistic" in a["message"] for a in alerts)


def test_alerts_down_dependencies():
    data = _healthy()
    data["database"] = {"ok": False}
    data["redis"] = {"ok": False}
    data["celery"] = {"ok": True, "workers": []}
    sources = {a["source"] for a in mon.build_alerts(data) if a["level"] == "critical"}
    assert {"database", "redis", "celery"} <= sources


def test_safe_isolates_errors():
    def collect_broken():
        raise RuntimeError("redis down")

    assert mon._safe(collect_broken) == {"ok": False, "error": "RuntimeError: redis down"}
    assert mon._safe(lambda: {"x": 1}) == {"ok": True, "x": 1}
