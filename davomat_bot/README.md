# Davomat Bot

Telegram bot (aiogram 3) — backend FaceID API ga ulanib davomat statistikasini
va Face ID tekshiruvini taqdim etadi.

## Struktura

```
davomat_bot/
├── main.py              # entrypoint
├── config.py            # .env sozlamalari
├── requirements.txt
├── .env.example
├── handlers/
│   ├── common.py        # /start, /menu, bosh menyu
│   ├── davomat.py       # Davomat olish flow
│   └── faceid.py        # Face ID flow (manual + QR)
├── keyboards/
│   └── inline.py        # inline tugmalar
├── states/
│   └── faceid.py        # FSM (qo'lda kiritish, QR)
├── services/
│   └── api_client.py    # backend bilan ishlovchi aiohttp client
└── utils/
    ├── callbacks.py     # CallbackData schemalari
    ├── formatters.py    # material design uslubidagi javob matnlari
    └── qr_decoder.py    # zxing-cpp — ID card QR o'qish
```

## Sozlash

1. Backend tomonida:
   - migratsiyani ishga tushiring: `alembic upgrade head` (davomat_bots, davomat_bot_regions yaratiladi).
   - Admin panelda foydalanuvchi yarating va `/api/v1/admin/api-keys` orqali API key oling.
   - Bot foydalanuvchilarini `davomat_bots` jadvaliga qo'shing (fio, telegram_id, region_id, zone_id).
     Qo'shimcha regionlar `davomat_bot_regions` orqali biriktiriladi.

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
BOT_TOKEN=...           # @BotFather'dan
API_BASE_URL=http://localhost:8000/api/v1
API_KEY=...             # backend admin paneldan
LOG_LEVEL=INFO
```

## Vazifalar

- `/start` — telegram_id bo'yicha ruxsat tekshiriladi va bosh menyu ko'rsatiladi.
- **Davomatni olish** → tayyor sessiyalar → kun+smena → biriktirilgan
  region/zone bo'yicha statistika.
- **Face ID** → ikkita usul:
  - Qo'lda kiritish (ps_ser, ps_num, JShShIR) → selfie → backend GTSP'dan rasm
    olib `compare_two_faces` orqali solishtiradi.
  - ID Card orqasidagi QR → bot pasport ma'lumotlarini avtomatik o'qiydi →
    selfie → solishtirish.

## Eslatma

- QR o'qish uchun `zxing-cpp` ishlatilgan — sof Python wheel orqali keladi
  (`pip install` bilan o'rnatiladi), tizim kutubxonalari kerakmas.
  Windows/Linux/macOS da bir xil ishlaydi.
- Aiogram 3 FSM uchun default `MemoryStorage` ishlatilgan — bir nechta worker
  yoki restart kerak bo'lsa, `RedisStorage` ga o'tkazing.
