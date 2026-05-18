"""Per-user, jarayon ichida saqlanadigan kichik state — tanlangan region.

Bot foydalanuvchisi bir nechta regionga biriktirilgan bo'lsa, `/start`
qadamida regionni tanlaydi va keyingi barcha so'rovlar shu region kesimida
amalga oshiriladi. Tanlangan region telegram_id orqali kalitlangan oddiy
dict'da turadi.

Saqlash strategiyasi:
  - Bot RAM'ida — restart bo'lsa qayta tanlash kerak.
  - FSM holatlariga aralashmaydi (state.clear bilan o'chmaydi).
  - Bitta region biriktirilgan rollarda ham bu yerda saqlanadi — kod yagona.
"""

from __future__ import annotations

import threading

_lock = threading.Lock()
_selected: dict[int, int] = {}


def set_region(telegram_id: int, region_id: int) -> None:
    """Tanlangan region id ni saqlash."""
    with _lock:
        _selected[int(telegram_id)] = int(region_id)


def get_region(telegram_id: int) -> int | None:
    """Tanlangan region id ni olish (yo'q bo'lsa None)."""
    with _lock:
        return _selected.get(int(telegram_id))


def clear_region(telegram_id: int) -> None:
    """Tanlovni tozalash — masalan, kirish ruxsati olib tashlanganda."""
    with _lock:
        _selected.pop(int(telegram_id), None)
