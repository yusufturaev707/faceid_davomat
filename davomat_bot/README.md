# Davomat Bot

Telegram bot (aiogram 3) — **Davomat Mini App**'ga kirish nuqtasi. Test
tadbirlari, statistika, kelmaganlar Excel'i, Face ID, davomatdan olib tashlash
va chetlatish — barchasi Mini App ichida bajariladi
(`frontend/src/miniapp`, backend `/api/v1/davomat-miniapp`).
To'liq arxitektura va deploy: [`deploy/DAVOMAT_MINIAPP.md`](../deploy/DAVOMAT_MINIAPP.md).

## Struktura

```
davomat_bot/
├── main.py              # entrypoint: komandalar + «Davomat» menyu tugmasi (WebApp)
├── config.py            # .env sozlamalari (WEBAPP_URL https shart)
├── requirements.txt
├── .env.example
├── handlers/
│   └── common.py        # /start, /menu, eski tugmalar va boshqa xabarlar → ilovaga yo'naltirish
├── keyboards/
│   └── inline.py        # «Davomat ilovasini ochish» (web_app) tugmasi
└── services/
    └── api_client.py    # backend: faqat ruxsat tekshiruvi (/davomat-bot/check)
```

## Sozlash

1. Backend: admin panelda bot foydalanuvchilarini (`davomat_bots`) qo'shing,
   `/api/v1/admin/api-keys` orqali API key oling. `backend/.env` da
   `DAVOMAT_BOT_TOKEN` (shu botning tokeni) va `DAVOMAT_MINIAPP_USER_ID` bo'lishi shart.

2. Bot:
   ```bash
   cd davomat_bot
   python -m venv .venv && .venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env   # va o'z qiymatlaringizni qo'ying
   python main.py
   ```

## .env

```
BOT_TOKEN=...           # @BotFather'dan (backend DAVOMAT_BOT_TOKEN bilan bir xil)
API_BASE_URL=http://localhost:8000/api/v1
API_KEY=...             # backend admin paneldan
WEBAPP_URL=https://face-id.uzbmb.uz/miniapp/
LOG_LEVEL=INFO
```

## Xulq

- `/start`, `/menu` — telegram_id bo'yicha ruxsat tekshiriladi. Ruxsat bo'lsa —
  salomlashish va «📱 Davomat ilovasini ochish» tugmasi; bo'lmasa — Telegram ID.
- Ishga tushganda barcha foydalanuvchilar uchun chat menyusi «Davomat» (Mini App)
  tugmasiga almashtiriladi.
- Mini App'dan oldingi xabarlardagi inline tugmalar bosilsa — "eskirgan" ogohlantirishi
  va ilovani ochish tugmasi.
- Bot FSM ishlatmaydi va holat saqlamaydi — bir nechta restart xavfsiz.
