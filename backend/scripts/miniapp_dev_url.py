"""Davomat Mini App'ni Telegram'siz, lokal brauzerda ochish uchun imzolangan URL.

    cd backend
    python scripts/miniapp_dev_url.py 811104615
    python scripts/miniapp_dev_url.py 811104615 --base http://localhost:5173/miniapp/

Telegram SDK initData'ni URL hash'idagi `tgWebAppData` dan o'qiydi — xuddi
Telegram klienti ochgandek. Imzo `backend/.env` dagi DAVOMAT_BOT_TOKEN bilan
qo'yiladi, shuning uchun backend shu URL'dagi foydalanuvchini haqiqiy deb
qabul qiladi. Faqat lokal ishlab chiqish uchun: production token bilan
yaratilgan URL — o'sha foydalanuvchi nomidan to'liq kirish demakdir.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.core.telegram_webapp import sign_init_data  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("telegram_id", type=int)
    parser.add_argument("--base", default="http://localhost:5173/miniapp/")
    parser.add_argument("--first-name", default="Dev")
    args = parser.parse_args()

    if not settings.DAVOMAT_BOT_TOKEN:
        sys.exit("backend/.env da DAVOMAT_BOT_TOKEN yo'q")

    init_data = sign_init_data(
        {
            "auth_date": str(int(time.time())),
            "user": json.dumps(
                {"id": args.telegram_id, "first_name": args.first_name},
                separators=(",", ":"),
            ),
        },
        settings.DAVOMAT_BOT_TOKEN,
    )
    fragment = urlencode(
        {
            "tgWebAppData": init_data,
            "tgWebAppVersion": "8.0",
            "tgWebAppPlatform": "unknown",
        }
    )
    print(f"{args.base}#{fragment}")


if __name__ == "__main__":
    main()
