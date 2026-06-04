# 📊 Statistic Bot

Abituriyentlar ro'yxati bo'yicha statistikani tashqi API'dan olib, **aiogram 3** asosida chiroyli va zamonaviy ko'rinishda taqdim etuvchi Telegram bot.

## Imkoniyatlar

- 🎓 **2026-yil qabuli** statistikasi va **2025-yil bilan solishtirma** (o'sish/kamayish foizi bilan)
- 👥 Jinsi bo'yicha taqsimot (vizual progress-bar bilan)
- 🎓 Bitiruv yili (joriy / avvalgi yillar)
- 💳 To'lov holati
- 📚 Ta'lim tili bo'yicha taqsimot (o'zbek / rus / qoraqalpoq / boshqa)
- 📍 Viloyatlar kesimida reytingli ro'yxat (🥇🥈🥉)
- 🔐 Faqat ruxsat etilgan adminlar uchun
- ⚡️ Kesh (cache) — API'ga ortiqcha so'rovlarni kamaytiradi

## O'rnatish

```bash
cd statistic_bot
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

## Sozlash

`.env.example` faylidan nusxa olib `.env` yarating va to'ldiring:

```bash
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/Mac
```

| O'zgaruvchi | Tavsif |
|-------------|--------|
| `BOT_TOKEN` | @BotFather dan olingan token (majburiy) |
| `API_URL` | Statistika qaytaradigan endpoint (majburiy) |
| `API_TOKEN` | Bearer token (ixtiyoriy) |
| `ADMIN_IDS` | Ruxsat etilgan Telegram ID lar (vergul bilan) |
| `CACHE_TTL` | Kesh muddati, soniyada (default: 60) |

## Ishga tushirish

```bash
python bot.py
```

## Buyruqlar

| Buyruq / Tugma | Vazifasi |
|----------------|----------|
| `/start` | Botni ishga tushirish va menyu |
| `/stat` yoki 📊 Statistika | So'nggi statistikani ko'rsatish |
| `/refresh` yoki 🔄 Yangilash | API'dan keshni chetlab yangilash |

## Loyiha tuzilishi

```
statistic_bot/
├── bot.py                  # Kirish nuqtasi
├── config.py               # .env sozlamalari
├── handlers/
│   └── statistics.py       # Buyruq/xabar handlerlari
├── keyboards/
│   └── menu.py             # Klaviaturalar
├── services/
│   └── api_client.py       # API klient + kesh
├── utils/
│   └── formatter.py        # Statistikani HTML matnga formatlash
├── requirements.txt
└── .env.example
```

## API javobi formati

Bot quyidagi tuzilishdagi JSON'ni kutadi:

```json
{
  "success": true,
  "body": {
    "status": 1,
    "data": [
      {
        "test_region_id": 1726,
        "region_name": "Toshkent shahri",
        "count_2025": 0, "male_2025": 0, "female_2025": 0,
        "graduated_2025": 0, "paid_2025": 0,
        "count_2026": 1, "male_2026": 1, "female_2026": 0,
        "graduated_2026": 0, "graduated_not_2026": 1, "paid_2026": 0,
        "uz_2026": 0, "ru_2026": 1, "qq_2026": 0, "lang_other_2026": 0
      }
    ]
  }
}
```
