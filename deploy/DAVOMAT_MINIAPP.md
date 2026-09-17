# Davomat Telegram Mini App — arxitektura va deploy

Davomat botining barcha imkoniyatlari (faol test tadbirlari, smena/kun/umumiy
statistika, kelmaganlar Excel'i, Face ID, davomatdan olib tashlash, chetlatish)
Telegram Mini App'ga ko'chirildi. Bot endi faqat ilovani ochib beradi.

## Arxitektura

```
Telegram klient ──(web_app tugma / «Davomat» menyusi)──► https://face-id.uzbmb.uz/miniapp/
      │                                                   (frontend dist/miniapp, nginx)
      │ initData (bot tokeni bilan imzolangan)
      ▼
Mini App (React) ──Authorization: tma <initData>──► /api/v1/davomat-miniapp/*  (FastAPI)
                                                     │ initData HMAC → telegram_id → davomat_bots
                                                     ├─ services/davomat_bot_service.py  (bot bilan umumiy logika)
                                                     └─ Telegram Bot API sendDocument (Excel → chat)

davomat_bot (aiogram) ── /start: ruxsat + «Davomat ilovasini ochish» tugmasi, menyu tugmasi
```

| Qism | Joyi |
|---|---|
| Mini App UI | `frontend/miniapp/index.html`, `frontend/src/miniapp/` (Vite'ning ikkinchi entry'si) |
| API | `backend/app/api/v1/endpoints/davomat_miniapp.py` |
| initData tekshiruvi | `backend/app/core/telegram_webapp.py` |
| Verify ticket, QR, sendDocument | `backend/app/services/davomat_miniapp.py` |
| Umumiy biznes-logika | `backend/app/services/davomat_bot_service.py` (bot endpointlari ham shuni ishlatadi) |
| Bot | `davomat_bot/` — faqat kirish nuqtasi |

## Xavfsizlik modeli

- **Kim?** — klient `telegram_id` yubormaydi. Har so'rovda Telegram imzolagan
  `initData` bot tokeni bilan HMAC orqali tekshiriladi, so'ng aktiv `davomat_bots`
  yozuvi olinadi. Foydalanuvchi bloklansa — keyingi so'rovdayoq 403.
  initData muddati: `DAVOMAT_MINIAPP_INIT_DATA_TTL` (default 24 soat).
- **Region** — har so'rovdagi `region_id` foydalanuvchiga biriktirilganligi
  tekshiriladi (bot kanalidagi bilan bir xil qoidalar).
- **Face ID → davomat** — `face-verify` muvaffaqiyatli bo'lsa backend imzolangan
  `verify_ticket` beradi (telegram_id, talabgor, smena, region, ball, selfie
  SHA-256, 10 daqiqa). `mark-attendance` faqat shu chipta bilan ishlaydi — klient
  Face ID'siz davomatga qo'sha olmaydi, ball yoki selfie'ni almashtira olmaydi.
- **Bot tokeni = Mini App kaliti.** Token kimda bo'lsa, istalgan foydalanuvchi
  nomidan initData yasay oladi. Token git'ga, log'ga, frontend'ga tushmasligi shart
  (`httpx` so'rov logidagi token avtomatik yashiriladi).

> ⚠️ **Deploydan oldin:** `davomat_bot/.env.example` da bot tokeni git tarixida
> bor. Mini App'ni yoqishdan oldin BotFather'da tokenni almashtiring
> (`/revoke`), yangisini faqat serverdagi `.env` fayllarga yozing.

## Deploy (tartib muhim: backend → frontend → bot)

### 1. Backend

```bash
cd /var/www/faceid_davomat
sudo git pull
sudo backend/venv/bin/pip install -r backend/requirements.txt   # zxing-cpp qo'shildi
```

`backend/.env` ga qo'shing:

```env
# davomat_bot/.env dagi BOT_TOKEN bilan AYNAN bir xil
DAVOMAT_BOT_TOKEN=<bot tokeni>
# Chetlatish yozuvlari (cheating_logs.user_id) shu foydalanuvchi nomidan yoziladi —
# bot API kalitining egasi (admin panel → API kalitlar → egasi, users.id)
DAVOMAT_MINIAPP_USER_ID=<users.id>
DAVOMAT_MINIAPP_INIT_DATA_TTL=86400
DAVOMAT_MINIAPP_VERIFY_TTL=600
```

Migratsiya yo'q. API'ni qayta ishga tushiring (gunicorn). Ikkala qiymat
bo'lmasa, Mini App endpointlari 503 qaytaradi — bot kanali ta'sirlanmaydi.

Server `api.telegram.org` ga chiqa olishi kerak (Excel faylni chatga yuborish).

### 2. Frontend

```bash
sudo bash deploy/frontend-deploy.sh
```

Build ikkala ilovani chiqaradi: `web/index.html` (admin) va `web/miniapp/index.html`.

### 3. nginx

Mavjud `try_files $uri $uri/ /index.html;` konfiguratsiyasi `/miniapp/` ni
o'zi topadi. Tekshiring va kerak bo'lsa qo'shing:

```nginx
# Telegram Web (web.telegram.org) Mini App'ni iframe ichida ochadi —
# /miniapp/ uchun X-Frame-Options DENY yoki frame-ancestors 'none' bo'lmasin.
location /miniapp/ {
    try_files $uri $uri/ /miniapp/index.html;
    add_header Cache-Control "no-cache";   # Telegram WebView eski index.html'ni keshlamasin
}

# Selfi (~0.3 MB) va QR rasmi (~1.5 MB) base64 JSON'da keladi.
client_max_body_size 10m;
```

> nginx'da `location` ichida bitta `add_header` bo'lsa, server darajasidagi
> barcha `add_header` (masalan, HSTS) shu location'ga **meros qilinmaydi** —
> kerakli xavfsizlik headerlarini `/miniapp/` ichida qayta yozing
> (`X-Frame-Options`dan tashqari).

`sudo nginx -t && sudo systemctl reload nginx`

### 4. Bot

`davomat_bot/.env` ga qo'shing:

```env
WEBAPP_URL=https://face-id.uzbmb.uz/miniapp/
```

```bash
sudo davomat_bot/venv/bin/pip install -r davomat_bot/requirements.txt
sudo systemctl restart faceid-davomat-bot.service
```

Bot ishga tushganda barcha foydalanuvchilar uchun chat menyusida «Davomat»
tugmasini o'rnatadi. `WEBAPP_URL` https bo'lmasa bot ishga tushmaydi.

## Tekshiruv ro'yxati

- [ ] `curl -s https://face-id.uzbmb.uz/miniapp/ | grep telegram-web-app` — sahifa bor.
- [ ] `curl -s -o /dev/null -w "%{http_code}" https://face-id.uzbmb.uz/api/v1/davomat-miniapp/me` → `401` (503 bo'lsa — `.env` to'liq emas).
- [ ] Botda `/start` → «📱 Davomat ilovasini ochish» tugmasi; chat pastida «Davomat» menyusi.
- [ ] Ilova ochiladi, 2+ viloyatli foydalanuvchida viloyat tanlash chiqadi.
- [ ] Smena → yuqorida jonli davomat kartasi; «Kelmaganlar ro'yxati» → Excel chatga keladi.
- [ ] Face ID: telefonda «QR kodni skanerlash» native skanerni ochadi; selfi → natija → «Davomatga qo'shish».
- [ ] Ro'yxatda yo'q foydalanuvchi ilovani ochsa — «Ruxsat berilmagan» va uning Telegram ID'si.

## Lokal ishlab chiqish

1. `backend/.env` ga istalgan test qiymat: `DAVOMAT_BOT_TOKEN=123456:local-dev`, `DAVOMAT_MINIAPP_USER_ID=1`.
2. `uvicorn app.main:app --reload --port 8000` va `cd frontend && npm run dev`.
3. Imzolangan URL (Telegram'siz, oddiy brauzerda):

   ```bash
   cd backend
   python scripts/miniapp_dev_url.py <telegram_id>
   ```

   Telegram tashqarisida native BackButton/MainButton o'rniga ilova ichidagi
   zaxira tugmalar chiqadi. Native QR skaner faqat Telegram mobil klientida.

Haqiqiy Telegram ichida sinash uchun HTTPS kerak (masalan, `cloudflared tunnel`
yoki `ngrok http 5173`) — tunnel URL'ini test botning `WEBAPP_URL` iga yozing.

## Tez-tez uchraydigan muammolar

| Belgi | Sabab | Yechim |
|---|---|---|
| Ilovada «Davomat ilovasi serverda sozlanmagan» | `DAVOMAT_BOT_TOKEN` yoki `DAVOMAT_MINIAPP_USER_ID` yo'q | `backend/.env`, API restart |
| «Telegram ma'lumotlari tasdiqlanmadi» | backend va botdagi tokenlar farq qiladi | ikkala `.env` da bir xil token |
| «Sessiya muddati tugagan» | ilova 24 soatdan ko'p ochiq turgan | ilovani yopib qayta ochish |
| Excel: «Telegram faylni qabul qilmadi» | token noto'g'ri yoki server `api.telegram.org` ga chiqa olmaydi | token / firewall |
| Excel: «Botni oching, /start bosing» | foydalanuvchi botni bloklagan | botda `/start` |
| Chetlatishda 503 | `DAVOMAT_MINIAPP_USER_ID` `users` jadvalida yo'q | to'g'ri `users.id` |
| QR rasmi: «QR rasmini o'qish serverda sozlanmagan» | backend venv'da `zxing-cpp` yo'q | `pip install -r requirements.txt` |
| Telegram Web'da oq ekran | nginx `/miniapp/` ga `X-Frame-Options: DENY` qo'shgan | yuqoridagi nginx bo'limi |
| Deploydan keyin eski ilova ochiladi | WebView keshi | `Cache-Control: no-cache` (nginx) |
