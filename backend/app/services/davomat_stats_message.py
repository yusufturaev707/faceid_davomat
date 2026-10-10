"""Davomat statistikasini Telegram xabariga aylantirish («Davomatni guruhga yuborish»).

Mini App tugmasi bosilganda ayni vaqtdagi statistika bot nomidan foydalanuvchi
chatiga HTML xabar bo'lib keladi — u uni guruhga forward qiladi. Shuning uchun
xabar o'zi-o'zini tushuntirishi kerak: tadbir, kun/smena, qaysi vaqt holati,
viloyat yakuni va har bir bino. Inline tugma yo'q (forward'da ma'nosiz).

Telegram bitta xabarga 4096 belgi beradi — binolar ko'p bo'lsa hisobot bir
necha xabarga bo'linadi, har biri «1/2» belgisi va sarlavha bilan.
"""

from __future__ import annotations

import html
from collections.abc import Iterable
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.test_session import TestSession
from app.schemas.davomat_bot import (
    BotRegionStat,
    BotSessionStatsResponse,
    BotZoneStat,
)
from app.services.davomat_bot_stats import BotStatsError, compute_bot_stats

UZ_TZ = timezone(timedelta(hours=5))

# Telegram limiti 4096 — HTML teglari ham hisobga kiradi; zaxira bilan.
MESSAGE_LIMIT = 3800

_MONTHS = (
    "yanvar", "fevral", "mart", "aprel", "may", "iyun",
    "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
)
_WEEKDAYS = ("Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba")


def _esc(text: str) -> str:
    """Telegram HTML uchun — faqat `<`, `>`, `&` (apostrof `&#x27;` bo'lib qolmasin)."""
    return html.escape(text or "", quote=False)


def _num(value: int) -> str:
    """`12345` → `12 345`."""
    return f"{value:,}".replace(",", " ")


def _percent(part: int, total: int) -> float:
    return round(part * 100 / total, 1) if total else 0.0


def _pct(value: float) -> str:
    """`94.4` → `94,4%`, `100.0` → `100%`."""
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{text.replace('.', ',')}%"


def _day(day: date) -> str:
    """`2026-10-10` → `10-oktabr, 2026 (Shanba)`."""
    return f"{day.day}-{_MONTHS[day.month - 1]}, {day.year} ({_WEEKDAYS[day.weekday()]})"


def _status_dot(percent: float) -> str:
    if percent >= 95:
        return "🟢"
    if percent >= 80:
        return "🟡"
    return "🔴"


def _progress_bar(percent: float, width: int = 10) -> str:
    filled = min(width, max(0, round(percent * width / 100)))
    return "🟩" * filled + "⬜" * (width - filled)


def _scope_line(stats: BotSessionStatsResponse) -> str:
    if stats.scope == "smena":
        day = f"{_day(stats.test_day)} • " if stats.test_day else ""
        return f"📅 {day}<b>{_esc(stats.smena_name)}</b>"
    if stats.scope == "day":
        day = f"{_day(stats.test_day)} • " if stats.test_day else ""
        return f"📅 {day}<b>Kun yakuni</b> (barcha smenalar)"
    return "📅 <b>Umumiy</b> — barcha kunlar va smenalar"


def _region_block(region: BotRegionStat) -> str:
    percent = _percent(region.entered, region.total)
    lines = [
        f"📍 <b>{_esc(region.region_name)}</b>",
        "<blockquote>"
        f"👥 Jami: <b>{_num(region.total)}</b>\n"
        f"✅ Keldi: <b>{_num(region.entered)}</b> · {_pct(percent)}\n"
        f"❌ Kelmadi: <b>{_num(region.not_entered)}</b> · "
        f"{_pct(_percent(region.not_entered, region.total))}"
        + (f"\n⛔ Chetlatildi: <b>{_num(region.cheating)}</b>" if region.cheating else "")
        + "</blockquote>",
        f"{_progress_bar(percent)} <b>{_pct(percent)}</b>",
    ]
    return "\n".join(lines)


def _zone_block(zone: BotZoneStat) -> str:
    percent = _percent(zone.entered, zone.total)
    rest = [f"Kelmadi: <b>{_num(zone.not_entered)}</b>"]
    if zone.cheating:
        rest.append(f"Chetlatildi: <b>{_num(zone.cheating)}</b>")
    return "\n".join(
        [
            f"{_status_dot(percent)} <b>{_esc(zone.zone_name)}</b>",
            f"├ Keldi: <b>{_num(zone.entered)}</b> / {_num(zone.total)} · <b>{_pct(percent)}</b>",
            f"└ {' · '.join(rest)}",
        ]
    )


_FOOTER = (
    "━━━━━━━━━━━━━━━\n"
    "🟢 95% va yuqori · 🟡 80–95% · 🔴 80% dan past\n"
    "<i>Keldi — binoga kirganlar (chetlatilganlar ham shu yerda).</i>"
)


def _pack(blocks: Iterable[str], limit: int) -> list[list[str]]:
    """Bloklarni (bino) bo'linmasdan xabarlarga joylash."""
    parts: list[list[str]] = [[]]
    size = 0
    for block in blocks:
        extra = len(block) + 2
        if parts[-1] and size + extra > limit:
            parts.append([])
            size = 0
        parts[-1].append(block)
        size += extra
    return parts


def format_stats_messages(
    stats: BotSessionStatsResponse,
    *,
    session_name: str,
    generated_at: datetime,
    limit: int = MESSAGE_LIMIT,
) -> list[str]:
    """Statistika → forward qilishga tayyor HTML xabar(lar).

    Talabgori yo'q binolar (0 / 0) tashlab ketiladi — Mini App ekrani bilan bir xil.
    """
    local = generated_at.astimezone(UZ_TZ)
    scope_line = _scope_line(stats)
    head = (
        f"📝 <b>{_esc(session_name)}</b>\n"
        f"{scope_line}\n"
        f"🕒 {local:%d.%m.%Y}, soat <b>{local:%H:%M}</b> holatiga"
    )

    blocks: list[str] = []
    for region in stats.regions:
        blocks.append(_region_block(region))
        zones = [z for z in region.zones if z.total > 0]
        if zones:
            title = f"🏢 <b>Binolar kesimida</b> ({len(zones)})"
            # Sarlavha birinchi bino bilan birga — yolg'iz qolib ketmasin.
            blocks.append(f"{title}\n\n{_zone_block(zones[0])}")
            blocks.extend(_zone_block(z) for z in zones[1:])

    if not blocks:
        blocks.append("Bu kontekstda talabgorlar yo'q.")

    # Sarlavha + futer har xabarda emas: sarlavha har birida (forward'da
    # alohida ko'rinadi), futer faqat oxirgisida.
    title_room = len(head) + 80
    parts = _pack(blocks, max(500, limit - title_room - len(_FOOTER)))
    total_parts = len(parts)

    messages: list[str] = []
    for index, part in enumerate(parts, start=1):
        counter = f" · {index}/{total_parts}" if total_parts > 1 else ""
        title = f"📊 <b>DAVOMAT HISOBOTI</b>{counter}"
        body = "\n\n".join(part)
        footer = f"\n\n{_FOOTER}" if index == total_parts else ""
        messages.append(f"{title}\n{head}\n\n{body}{footer}")
    return messages


def build_stats_messages(
    db: Session,
    *,
    session_id: int,
    session_smena_id: int | None,
    test_day: date | None,
    allowed_region_ids: set[int],
    now: datetime | None = None,
) -> tuple[list[str], int]:
    """(xabarlar, jami talabgorlar soni). `BotStatsError` — kontekst topilmadi."""
    session_name = db.scalar(select(TestSession.name).where(TestSession.id == session_id))
    if session_name is None:
        raise BotStatsError("Test tadbiri topilmadi")
    stats = compute_bot_stats(
        db,
        session_id=session_id,
        session_smena_id=session_smena_id,
        test_day=test_day,
        allowed_region_ids=allowed_region_ids,
    )
    total = sum(r.total for r in stats.regions)
    messages = format_stats_messages(
        stats,
        session_name=session_name,
        generated_at=now or datetime.now(UZ_TZ),
    )
    return messages, total
