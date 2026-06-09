"""Statistika bot foydalanuvchilarini `statistic_bot/.env` dan seed qilish.

Ishlatish: cd backend && python -m app.db.seed_statistic_bot

`statistic_bot/.env` faylidagi `ADMIN_IDS` va `STAFF_IDS` telegram id larini
`statistic_bots` jadvaliga ko'chiradi:
  - ADMIN_IDS → role=1 (Admin)
  - STAFF_IDS → role=3 (Xodim)

Idempotent: mavjud telegram_id qayta yaratilmaydi (status/rol o'zgartirilmaydi —
adminkada qo'lda boshqariladi). Yangi id lar qo'shiladi.

Eslatma: seed faqat boshlang'ich qiymat. Keyinchalik foydalanuvchilar
admin panel orqali tahrirlanadi (rol, status, FIO).
"""

from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.statistic_bot import ROLE_ADMIN, ROLE_XODIM, StatisticBot

# backend/app/db/seed_statistic_bot.py → parents[3] = repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENV_PATH = _REPO_ROOT / "statistic_bot" / ".env"


def _parse_env_ids(env_path: Path, key: str) -> list[int]:
    """`.env` faylidan `KEY=1,2,3` qatorini o'qib, id ro'yxatini qaytaradi."""
    if not env_path.exists():
        return []
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=\s*(.*)$")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("#"):
            continue
        m = pattern.match(line)
        if not m:
            continue
        raw = m.group(1).strip().strip('"').strip("'")
        ids: list[int] = []
        for part in raw.replace(" ", "").split(","):
            if not part:
                continue
            try:
                ids.append(int(part))
            except ValueError:
                continue
        return ids
    return []


def _upsert(db: Session, telegram_id: int, role: int, fio: str) -> bool:
    """Yangi yozuv qo'shadi (mavjud bo'lsa tegmaydi). True = qo'shildi."""
    existing = db.execute(
        select(StatisticBot.id).where(StatisticBot.telegram_id == telegram_id)
    ).scalar_one_or_none()
    if existing is not None:
        return False
    db.add(
        StatisticBot(
            fio=fio,
            telegram_id=telegram_id,
            role=role,
            status=True,
        )
    )
    return True


def seed() -> None:
    admin_ids = _parse_env_ids(_ENV_PATH, "ADMIN_IDS")
    staff_ids = _parse_env_ids(_ENV_PATH, "STAFF_IDS")

    if not admin_ids and not staff_ids:
        print(f"Ogohlantirish: {_ENV_PATH} da ADMIN_IDS/STAFF_IDS topilmadi.")
        return

    db: Session = SessionLocal()
    added = 0
    try:
        for tid in admin_ids:
            if _upsert(db, tid, ROLE_ADMIN, "Bot admin"):
                added += 1
        for tid in staff_ids:
            if _upsert(db, tid, ROLE_XODIM, "Bot xodim"):
                added += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(
        f"Statistic bot seed tugadi: ADMIN_IDS={admin_ids} (role=1), "
        f"STAFF_IDS={staff_ids} (role=3), yangi qo'shildi: {added} ta."
    )


if __name__ == "__main__":
    seed()
