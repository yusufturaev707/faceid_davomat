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


def _region(zones, *, region_id=1, name="Buxoro viloyati"):
    total = sum(z.total for z in zones)
    entered = sum(z.entered for z in zones)
    return BotRegionStat(
        region_id=region_id,
        region_name=name,
        region_number=region_id,
        total=total,
        entered=entered,
        not_entered=total - entered,
        cheating=sum(z.cheating for z in zones),
        zones=zones,
    )


def _stats(zones=None, *, scope="smena", regions=None):
    return BotSessionStatsResponse(
        session_id=1,
        session_smena_id=5 if scope == "smena" else 0,
        test_day=None if scope == "total" else date(2026, 10, 10),
        smena_number=1,
        smena_name="1-smena" if scope == "smena" else "Kun yakuni",
        scope=scope,
        regions=regions if regions is not None else [_region(zones)],
    )


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def test_header_test_name_date_and_smena_on_separate_lines():
    zones = [_zone(1, "1-bino", 10, 9)]
    [msg] = format_stats_messages(
        _stats(zones),
        session_name="Oktabr sessiyasi",
        test_name="Milliy sertifikat imtihoni (matematika)",
        generated_at=NOW,
    )
    lines = msg.split("\n")
    assert lines[0] == "📊 <b>DAVOMAT HISOBOTI</b>"
    assert lines[1] == ""  # sarlavhadan keyin bo'sh qator
    assert lines[2] == "🗂 Oktabr sessiyasi"
    assert lines[3] == "📝 <b>Milliy sertifikat imtihoni (matematika)</b>"
    assert "📅 <b>10-oktabr, 2026-yil</b> · Shanba" in lines
    assert "🕘 <b>1-smena</b>" in lines
    # Yuqorida vaqt yo'q, pastda — yuborilgan vaqt; ranglar izohi yo'q
    assert "holatiga" not in msg
    assert msg.endswith("🕒 <i>Yuborildi: 10.10.2026 · 10:42</i>")
    assert "80%" not in msg and "guruh" not in msg


def test_single_active_zone_shows_only_region():
    zones = [_zone(1, "Yagona bino", 200, 196, cheating=2), _zone(2, "Bo'sh bino", 0, 0)]
    [msg] = format_stats_messages(_stats(zones), session_name="S", generated_at=NOW)
    text = _strip_tags(msg)

    assert "📍 BUXORO VILOYATI" in text
    assert "▰▰▰▰▰▰▰▰▰▰  98%" in text
    assert "Jami: 196" not in text and "Jami: 200" in text
    assert "✅ Keldi: 196\n❌ Kelmadi: 4\n⛔ Chetlatildi: 2" in text
    assert "Yagona bino" not in text and "Binolar" not in text
    assert "Bo'sh bino" not in text


def test_several_zones_are_nested_under_region():
    zones = [
        _zone(1, "1-bino", 200, 196, cheating=2),
        _zone(2, "Bo'sh bino", 0, 0),
        _zone(3, "3-bino", 100, 70),
    ]
    [msg] = format_stats_messages(_stats(zones), session_name="S", generated_at=NOW)
    text = _strip_tags(msg)

    assert "Jami: 300" in text and "Keldi: 266" in text and "88,7%" in text
    # Binolar viloyat blokiga yopishgan (bo'sh qatorsiz), daraxt └ bilan yopiladi
    assert "</blockquote>\n🏢 Binolar · 2 ta\n├ 🟢 1-bino\n" in msg
    assert "✅ 196/200 · 98% · ❌ 4 · ⛔ 2" in text
    assert "└ 🔴 3-bino" in text and "✅ 70/100 · 70% · ❌ 30" in text
    assert "Bo'sh bino" not in text


def test_regions_without_students_are_skipped():
    regions = [
        _region([_zone(1, "A", 10, 10)], region_id=1, name="Buxoro"),
        _region([_zone(2, "B", 0, 0)], region_id=2, name="Navoiy"),
    ]
    [msg] = format_stats_messages(_stats(regions=regions), session_name="S", generated_at=NOW)
    assert "BUXORO" in msg and "NAVOIY" not in msg


def test_html_is_escaped_without_apostrophe_entities():
    zones = [_zone(1, "O'quv <markaz> & bino", 10, 10), _zone(2, "2-bino", 5, 5)]
    [msg] = format_stats_messages(_stats(zones), session_name="A & B", generated_at=NOW)
    assert "O'quv &lt;markaz&gt; &amp; bino" in msg
    assert "A &amp; B" in msg
    assert "&#x27;" not in msg


def test_day_and_total_scope_headers():
    zones = [_zone(1, "1-bino", 20, 20)]
    [day] = format_stats_messages(_stats(zones, scope="day"), session_name="S", generated_at=NOW)
    assert "📅 <b>10-oktabr, 2026-yil</b> · Shanba" in day
    assert "🕘 <b>Kun yakuni</b> · barcha smenalar" in day

    [total] = format_stats_messages(_stats(zones, scope="total"), session_name="S", generated_at=NOW)
    assert "📅 <b>Barcha kunlar</b>\n🕘 <b>Barcha smenalar</b>" in total


def test_long_report_is_split_into_numbered_messages_under_limit():
    zones = [_zone(i, f"Juda uzun nomli o'quv binosi raqami {i}", 300, 280) for i in range(1, 61)]
    msgs = format_stats_messages(_stats(zones), session_name="S", generated_at=NOW)

    assert len(msgs) > 1
    assert all(len(m) <= 4096 for m in msgs)
    for i, m in enumerate(msgs, start=1):
        assert m.startswith(f"📊 <b>DAVOMAT HISOBOTI</b> · {i}/{len(msgs)}\n\n")
        assert "1-smena" in m  # har bir qism o'zi tushunarli
        # Har qismdagi daraxt └ bilan yopiladi
        assert "\n└ " in m
    assert "binolar (davomi)" in msgs[1]
    # Har bino aynan bir marta, yuborilgan vaqt faqat oxirida
    joined = "\n".join(msgs)
    for i in range(1, 61):
        assert joined.count(f"raqami {i}\n") == 1
    assert "Yuborildi" in msgs[-1] and "Yuborildi" not in msgs[0]
