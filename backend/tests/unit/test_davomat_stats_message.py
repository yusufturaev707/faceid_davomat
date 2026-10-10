"""«Davomatni guruhga yuborish» — statistika → Telegram HTML xabar."""

from __future__ import annotations

import re
from datetime import date, datetime, timezone

from app.schemas.dashboard_stats import FullGroupItem
from app.schemas.davomat_bot import BotRegionStat, BotSessionStatsResponse, BotZoneStat
from app.services.davomat_stats_message import format_stats_messages

NOW = datetime(2026, 10, 10, 5, 42, tzinfo=timezone.utc)  # 10:42 Toshkent


def _zone(zone_id, name, total, entered, *, cheating=0, total_groups=0, full=()):
    return BotZoneStat(
        zone_id=zone_id,
        zone_name=name,
        zone_number=zone_id,
        total=total,
        entered=entered,
        not_entered=total - entered,
        cheating=cheating,
        total_groups=total_groups,
        full_groups=[FullGroupItem(gr_n=g, session_smena_id=5, total=10) for g in full],
    )


def _stats(zones, *, scope="smena", region_name="Buxoro viloyati"):
    total = sum(z.total for z in zones)
    entered = sum(z.entered for z in zones)
    return BotSessionStatsResponse(
        session_id=1,
        session_smena_id=5 if scope == "smena" else 0,
        test_day=date(2026, 10, 10),
        smena_number=1,
        smena_name="1-smena" if scope == "smena" else "Kun yakuni",
        scope=scope,
        regions=[
            BotRegionStat(
                region_id=1,
                region_name=region_name,
                region_number=6,
                total=total,
                entered=entered,
                not_entered=total - entered,
                cheating=sum(z.cheating for z in zones),
                zones=zones,
            )
        ],
    )


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def test_smena_report_has_context_totals_and_zone_lines():
    zones = [
        _zone(1, "1-bino", 200, 196, cheating=2, total_groups=10, full=[7, 2]),
        _zone(2, "Bo'sh bino", 0, 0),
        _zone(3, "3-bino", 100, 70),
    ]
    [msg] = format_stats_messages(_stats(zones), session_name="Milliy sertifikat", generated_at=NOW)
    text = _strip_tags(msg)

    assert "Milliy sertifikat" in text
    assert "10-oktabr, 2026 (Shanba) • 1-smena" in text
    assert "10.10.2026, soat 10:42 holatiga" in text
    assert "Jami: 300" in text and "Keldi: 266 · 88,7%" in text
    assert "🟢 1-bino" in text and "Keldi: 196 / 200 · 98%" in text
    assert "🔴 3-bino" in text
    # Talabgori yo'q bino tashlab ketiladi
    assert "Bo'sh bino" not in text
    assert "Binolar kesimida (2)" in text
    # 100% kelgan guruhlar hisobotga kirmaydi
    assert "guruh" not in text


def test_html_is_escaped_without_apostrophe_entities():
    zones = [_zone(1, "O'quv <markaz> & bino", 10, 10)]
    [msg] = format_stats_messages(_stats(zones), session_name="A & B", generated_at=NOW)
    assert "O'quv &lt;markaz&gt; &amp; bino" in msg
    assert "A &amp; B" in msg
    assert "&#x27;" not in msg


def test_day_scope_header():
    zones = [_zone(1, "1-bino", 20, 20, total_groups=4, full=[1, 2])]
    [msg] = format_stats_messages(_stats(zones, scope="day"), session_name="S", generated_at=NOW)
    text = _strip_tags(msg)
    assert "Kun yakuni (barcha smenalar)" in text
    assert "guruh" not in text


def test_long_report_is_split_into_numbered_messages_under_limit():
    zones = [
        _zone(i, f"Juda uzun nomli o'quv binosi raqami {i}", 300, 280, total_groups=20, full=range(1, 15))
        for i in range(1, 41)
    ]
    msgs = format_stats_messages(_stats(zones), session_name="S", generated_at=NOW)

    assert len(msgs) > 1
    assert all(len(m) <= 4096 for m in msgs)
    for i, m in enumerate(msgs, start=1):
        assert f"DAVOMAT HISOBOTI</b> · {i}/{len(msgs)}" in m
        assert "1-smena" in m  # har bir qism o'zi tushunarli
    # Har bino aynan bir marta, futer faqat oxirida
    joined = "\n".join(msgs)
    for i in range(1, 41):
        assert joined.count(f"raqami {i}</b>") == 1
    assert "80% dan past" in msgs[-1] and "80% dan past" not in msgs[0]
