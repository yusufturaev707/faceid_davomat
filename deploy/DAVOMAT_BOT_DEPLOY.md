# Davomat bot — Linux production deploy (systemd)

Bu yo'riqnoma `davomat_bot` ni Linux serverda **alohida virtual env** va
**alohida systemd service** sifatida ishga tushirish bo'yicha.

Bot backend (`/api/v1`) bilan **HTTP orqali** ulanadi va `X-API-Key`
ishlatadi — ya'ni backend bilan bir xil mashinada ishlashi shart emas,
lekin xuddi shu serverga qo'yish odatda eng oson va xavfsiz variant.

## Old shart

- Backend (faceid API) allaqachon serverda ishlab turibdi:
  `https://face-id.uzbmb.uz/api/v1` (yoki `http://127.0.0.1:8000/api/v1`).
- Admin paneldan **bot uchun API key** yaratilgan.
- `davomat_bots` jadvalida bot foydalanuvchilari qo'shilgan
  (telegram_id + region/zone biriktirilgan).
- Serverda `python3.11+`, `git` mavjud. QR o'qish uchun `zxing-cpp`
  ishlatiladi — sof Python wheel orqali keladi, tizim kutubxonasi kerakmas.

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip git
```

## 1) Loyihani clone qilish (yoki yangilash)

Backend bilan bir xil katalogni ishlatamiz (`/var/www/faceid_davomat/`),
shunday qilib backend systemd unit'lari bilan path konventsiyasi mos
bo'ladi.

```bash
sudo mkdir -p /var/www/faceid_davomat
sudo chown -R root:www-data /var/www/faceid_davomat

# Agar backend allaqachon shu yerda bo'lsa, faqat pull qiling:
cd /var/www/faceid_davomat
sudo git pull

# Aks holda — clone:
# sudo git clone <repo_url> /var/www/faceid_davomat
```

Natijada quyidagi struktura bo'ladi:
```
/var/www/faceid_davomat/
├── backend/            # FastAPI (alohida venv)
├── davomat_bot/        # <-- biz shuni deploy qilamiz
└── deploy/systemd/
```

## 2) Alohida virtual env yaratish

Backend env'i bilan **aralashtirilmaydi** — bot'ning aiogram, aiohttp,
zxing-cpp bog'liqliklari bekendning insightface/onnxruntime bilan
to'qnashmasligi va versiyalar bir-biriga zarar bermasligi uchun.

```bash
cd /var/www/faceid_davomat/davomat_bot
sudo python3.11 -m venv venv
sudo ./venv/bin/pip install --upgrade pip
sudo ./venv/bin/pip install -r requirements.txt
```

Tekshirish:
```bash
./venv/bin/python -c "import aiogram, aiohttp, zxingcpp; print('OK')"
```

## 3) `.env` faylni sozlash

```bash
sudo cp .env.example .env
sudo chmod 640 .env
sudo chown root:www-data .env
sudo nano .env
```

Quyidagi qiymatlarni to'g'rilang:
```env
BOT_TOKEN=<BotFather'dan olingan token>
API_BASE_URL=http://127.0.0.1:8000/api/v1
# yoki:  https://face-id.uzbmb.uz/api/v1
API_KEY=<admin paneldan olingan X-API-Key>
LOG_LEVEL=INFO
```

> Maslahat: backend bir serverda bo'lsa, `127.0.0.1` orqali kirgan
> ma'qul — ortiqcha TLS overhead'i bo'lmaydi, tashqi tarmoqdan ham
> chiqmaydi.

## 4) Log katalogini yaratish

systemd service log'larni quyidagi joyga yozadi:

```bash
sudo mkdir -p /var/www/faceid_davomat/davomat_bot/logs
sudo chown -R root:www-data /var/www/faceid_davomat/davomat_bot/logs
sudo chmod 750 /var/www/faceid_davomat/davomat_bot/logs
```

## 5) systemd unit'ni o'rnatish

Repo'da `deploy/systemd/faceid-davomat-bot.service` tayyor — uni systemd
katalogiga symlink qilamiz (yangilanishlarda `git pull` qilsa, unit
fayli ham yangilanadi):

```bash
sudo ln -s /var/www/faceid_davomat/deploy/systemd/faceid-davomat-bot.service \
           /etc/systemd/system/faceid-davomat-bot.service

sudo systemctl daemon-reload
sudo systemctl enable faceid-davomat-bot.service
sudo systemctl start  faceid-davomat-bot.service
```

Holatni tekshirish:
```bash
sudo systemctl status faceid-davomat-bot.service
sudo journalctl -u faceid-davomat-bot.service -f
# yoki log fayli:
tail -f /var/www/faceid_davomat/davomat_bot/logs/bot.log
```

## 6) Yangilash (yangilanishlar kelganda)

```bash
cd /var/www/faceid_davomat
sudo git pull

# Agar requirements.txt o'zgargan bo'lsa:
sudo /var/www/faceid_davomat/davomat_bot/venv/bin/pip install \
     -r /var/www/faceid_davomat/davomat_bot/requirements.txt

sudo systemctl restart faceid-davomat-bot.service
```

## 7) Tekshiruv ro'yxati

- [ ] `systemctl status faceid-davomat-bot` → `active (running)`.
- [ ] `journalctl -u faceid-davomat-bot -n 50` da
      "Davomat bot ishga tushdi (long polling)" satri bor.
- [ ] Telegramda `/start` bosilganda bot javob beradi.
- [ ] "Faol test tadbirlari" → kun+smena → "Davomatni olish" / "Kelmaganlar
      ro'yxatini olish" buttonlari ishlaydi va Excel keladi.

## 8) Tez-tez uchraydigan muammolar

| Belgi | Sabab | Yechim |
|---|---|---|
| `403 Botdan foydalanish ruxsati yo'q` | `davomat_bots` jadvalida shu telegram_id yo'q yoki `is_active=False` | Admin panel orqali qo'shing / aktivlashtiring |
| `401/403 X-API-Key` | `.env` dagi `API_KEY` xato / muddati o'tgan | Admin panelda yangi key oling va `.env` ga yozing, restart qiling |
| `aiohttp.ClientConnectorError: Cannot connect to host` | `API_BASE_URL` noto'g'ri yoki backend o'chgan | `curl http://127.0.0.1:8000/api/v1/lookup/...` bilan tekshiring |
| `ModuleNotFoundError: No module named 'zxingcpp'` | venv'da paket o'rnatilmagan | `./venv/bin/pip install -r requirements.txt` |
| Bir nechta instans bir vaqtda javob beradi | Eski jarayon qolib ketgan | `ps aux \| grep "davomat_bot/main.py"` → `kill`, keyin systemd orqali ishga tushiring |

## 9) Nima uchun alohida venv?

- **Versiyalar to'qnashuvi**: backend `pydantic==2.10.4`, bot
  `pydantic==2.9.2` — bitta env'da bittasi yo'qoladi.
- **Restart izolyatsiyasi**: backend (uvicorn/celery) restart bo'lganda
  bot to'xtamasligi, va aksincha.
- **Engil image**: bot uchun `insightface`, `onnxruntime`, `opencv`
  kerakmas — uni bot env'iga tortmaymiz.
- **Xavfsizlik**: API key faqat bot env'ida, backend `.env` bilan
  aralashtirilmaydi.
