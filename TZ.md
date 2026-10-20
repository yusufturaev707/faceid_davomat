# TEXNIK TOPSHIRIQ

## «FaceID / Davomat» axborot tizimi — funksiyalari, vazifalari va ish jarayonlari tavsifi
### (kiberxavfsizlik ekspertizasi uchun)

| | |
|---|---|
| Tizim nomi | FaceID / Davomat — milliy imtihonlarda nomzodlarni yuz orqali identifikatsiya qilish va davomatni hisobga olish axborot tizimi |
| Tizim manzili | `https://face-id.uzbmb.uz` (API — `/api/v1`, Telegram Mini App — `/miniapp/`) |
| Hujjat versiyasi / sanasi | 1.0 / 15.10.2026 |
| Tizim egasi (buyurtmachi) | ______________________________ |
| Ekspertiza o'tkazuvchi tashkilot | ______________________________ |
| Mas'ul shaxs | ______________________________ |

---

## Mundarija

1. Umumiy ma'lumot
2. Tizimning maqsadi va vazifalari
3. Tizim foydalanuvchilari va ularning vakolatlari
4. Tizim tarkibi (komponentlar)
5. Tizimning asosiy obyektlari va ularning holatlari
6. Ish jarayonlari (bosqichma-bosqich)
7. Tizim funksiyalarining to'liq ro'yxati (modullar bo'yicha)
8. Tashqi tizimlar bilan o'zaro aloqa
9. Qayta ishlanadigan ma'lumotlar
10. Tizimdagi xavfsizlik mexanizmlari
11. Texnik ta'minot va joylashtirish muhiti
12. Ekspertizaga qo'yiladigan talablar
13. Ilovalar: A — API endpointlar, B — ruxsatlar katalogi

---

## 1. Umumiy ma'lumot

### 1.1. Tizim nima uchun yaratilgan

Milliy imtihonlarda (CEFR, Milliy sertifikat, IIV, OTM-DTM va boshqalar) imtihon binosiga nomzod o'rniga
boshqa shaxs kirishining oldini olish, nomzodlarning kelganini aniq hisobga olish, qoidabuzarlarni chetlatish va
butun respublika bo'yicha davomatni real vaqtda kuzatish uchun.

Tizim nomzodning imtihon kuni olingan yuz rasmini (selfi) uning davlat bazasidagi pasport rasmi bilan
sun'iy intellekt (yuz tanish) yordamida solishtiradi va natijani davomat sifatida qayd etadi.

### 1.2. Ishlash ko'lami

- Bir test tadbirida — 700 mingdan ortiq nomzod, bir necha kun va har kunda bir necha smena.
- Respublikaning barcha viloyatlaridagi yuzlab imtihon binolari.
- Har bir binoda — desktop klient o'rnatilgan kompyuterlar va Telegram Mini App orqali ishlovchi xodimlar.

### 1.3. Atamalar

| Atama | Ma'nosi |
|---|---|
| Nomzod (talabgor) | Imtihon topshiruvchi shaxs |
| Test | Imtihon turi (CEFR, MS, IIV, OTM-DTM ...) |
| Test tadbiri (test sessiya) | Muayyan test bo'yicha boshlanish va tugash sanasi bo'lgan imtihon davri |
| Smena | Test tadbirining aniq kuni va vaqt bo'lagi (masalan, 10-oktabr, 1-smena) |
| Viloyat / Bino (zona) | Imtihon o'tkaziladigan hudud va undagi bino |
| Guruh (`gr_n`) | Bino ichidagi auditoriya/guruh raqami |
| Joy (`sp_n`) | Nomzodning o'rni yoki Proctoring kompyuter raqami |
| JShShIR (PINFL) | Shaxsiy identifikatsiya raqami (14 raqam); tizimda `imei` maydoni |
| GTSP | Pasport ma'lumotlari va pasport rasmini beruvchi davlat xizmati |
| Embedding | Yuz rasmidan olingan 512 o'lchamli raqamli vektor (biometrik shablon) |
| Davomat | Nomzod kelganini qayd etish |
| Chetlatish | Qoidabuzarlik sababli nomzodni imtihondan chiqarish |
| Qora ro'yxat | Chetlatilgan shaxslar (JShShIR bo'yicha) ro'yxati |
| Ariza bergan (`is_applied`) | To'lovni qaytarish uchun ariza bergan, imtihonga kiritilmaydigan nomzod |
| Proctoring | Kompyuterda imtihon o'tkazish va nazorat qilish tizimi (tashqi) |
| Mini App | Telegram ichida ochiladigan veb-ilova |

---

## 2. Tizimning maqsadi va vazifalari

### 2.1. Maqsad
Imtihonlarda shaxsni ishonchli identifikatsiya qilish, davomat va qoidabuzarliklarni yagona markazlashgan
tizimda hisobga olish, rahbariyatni real vaqtdagi ma'lumot bilan ta'minlash.

### 2.2. Vazifalar

| № | Vazifa | Qisqacha mazmuni |
|---|---|---|
| V1 | Test tadbirlarini boshqarish | Tadbir yaratish, kun va smenalarni belgilash, tayyorlash bosqichlarini boshqarish |
| V2 | Nomzodlar bazasini shakllantirish | Tashqi API'lardan yoki Excel fayldan nomzodlar ro'yxati va pasport rasmlarini yuklash |
| V3 | Pasport ma'lumotlarini dolzarblashtirish | Eskirgan pasport seriya/raqamlarini Excel, rasm arxivi yoki E-GOV PSN orqali yangilash |
| V4 | Biometrik shablonlarni tayyorlash | Har bir nomzod pasport rasmidan yuz embeddingini hisoblash, rasmsiz/yuzsiz nomzodlarni aniqlash |
| V5 | Kompyuterlarni biriktirish | Proctoring tizimidagi kompyuterlarni nomzodlarga taqsimlash |
| V6 | Imtihon kuni shaxsni tasdiqlash | Nomzod yuzini pasport rasmi bilan solishtirish (desktop klient va Mini App) |
| V7 | Davomatni qayd etish | Kelgan nomzodlarni belgilash, kirish vaqti va selfi rasmini saqlash, kerak bo'lsa bekor qilish |
| V8 | Qoidabuzarlarni chetlatish | Chetlatish sababini qayd etish, nomzodni qora ro'yxatga kiritish |
| V9 | Monitoring va hisobotlar | Viloyat/bino/smena kesimida davomat statistikasi, kelmaganlar ro'yxati, Excel/PDF hisobotlar |
| V10 | Natijalarni tahlil qilish | Imtihon natijalarini davomat va chetlatish ma'lumotlari bilan solishtirish |
| V11 | Tashqi tizimlarga xizmat ko'rsatish | Rasm sifatini tekshirish va ikki yuzni solishtirish xizmati (API) |
| V12 | Pasport ma'lumotlarini olish | Seriya/raqam va JShShIR bo'yicha GTSP'dan shaxs ma'lumotini olish |
| V13 | Qabul statistikasi | Qabul ko'rsatkichlarini Telegram bot va admin panel orqali ko'rsatish |
| V14 | Kirish huquqlarini boshqarish | Foydalanuvchilar, rollar, ruxsatlar, API kalitlar, bot foydalanuvchilari |
| V15 | Audit | Kirish urinishlari, tekshiruv loglari, onlayn sessiyalar |

---

## 3. Tizim foydalanuvchilari va ularning vakolatlari

| № | Foydalanuvchi | Qayerdan ishlaydi | Asosiy vakolatlari |
|---|---|---|---|
| 1 | Tizim administratori | Admin panel | Barcha funksiyalar; foydalanuvchi, rol, ruxsat, API kalit boshqaruvi |
| 2 | Markaziy apparat xodimi | Admin panel | Test tadbirlarini tayyorlash, barcha viloyatlar statistikasi, hisobotlar (rolga biriktirilgan ruxsatlar doirasida) |
| 3 | Viloyat xodimi | Admin panel | Faqat o'z viloyati nomzodlari, davomati, chetlatishlari va statistikasi |
| 4 | Bino operatori | Desktop klient | O'z binosi (yoki viloyati ichidagi tanlangan bino) nomzodlarini Face ID orqali tekshirish, davomat va chetlatishni yuborish |
| 5 | Imtihon markazi xodimi (davomat) | Telegram Mini App | Biriktirilgan viloyat(lar)da Face ID, davomat, davomatdan olib tashlash, chetlatish, statistika |
| 6 | Rahbariyat / statistika foydalanuvchisi | Statistika Telegram boti, admin panel «Qabul» sahifasi | Qabul ko'rsatkichlarini ko'rish (Admin / Rahbar / Xodim darajalari) |
| 7 | Tashqi axborot tizimi | REST API (`X-API-Key`) | Rasm tekshirish, ikki yuzni solishtirish, embedding olish |
| 8 | Telegram botlar (davomat, statistika) | REST API (`X-API-Key`) | Bot foydalanuvchisi nomidan backend'ga murojaat |

Vakolatlar **ruxsat kodlari** (101 ta, B ilova) orqali rolga biriktiriladi. Ruxsatdan alohida **viloyat doirasi**
qo'llaniladi: `student:all_regions` ruxsati bo'lmagan foydalanuvchi faqat o'z viloyati ma'lumotlarini ko'radi.

Telegram foydalanuvchilari (5, 6) admin panel foydalanuvchilari emas — ular alohida ro'yxatlarda
(«Davomat bot foydalanuvchilari», «Statistika bot foydalanuvchilari») Telegram ID bo'yicha ro'yxatga olinadi:
- davomat xodimiga rol va bir yoki bir nechta viloyat biriktiriladi (viloyat darajasidagi rolga — aniq bitta);
- statistika foydalanuvchisiga daraja beriladi: 1 — Admin, 2 — Rahbar, 3 — Xodim (2 va 3 to'lov holati va
  o'tgan yil ma'lumotlarini ko'rmaydi).

---

## 4. Tizim tarkibi (komponentlar)

```
 ┌───────────────┐  ┌────────────────┐  ┌─────────────────┐  ┌──────────────┐  ┌───────────────┐
 │ Admin panel   │  │ Desktop klient │  │ Telegram        │  │ Telegram     │  │ Tashqi        │
 │ (brauzer)     │  │ (bino, PyQt6)  │  │ Mini App        │  │ botlar       │  │ tizimlar      │
 └──────┬────────┘  └──────┬─────────┘  └──────┬──────────┘  └──────┬───────┘  └──────┬────────┘
        │ JWT              │ JWT/API kalit     │ initData           │ API kalit       │ API kalit
        └──────────────────┴─────────┬─────────┴────────────────────┴─────────────────┘
                                     ▼
                     nginx (HTTPS) → Backend API (FastAPI, /api/v1)
                                     │
             ┌───────────────────────┼─────────────────────────────┐
             ▼                       ▼                             ▼
      PostgreSQL (asosiy baza)   Redis (navbat, kesh,       Celery fon xizmatlari
                                 sessiya nazorati)          (yuklash, embedding, rasm, bron)
                                     │
      Chiquvchi aloqalar: GTSP, E-GOV PSN, CEFR/MS/IIV/OTM API, OTM binolar API,
                          Proctoring, Telegram Bot API, qabul statistikasi API
```

| № | Komponent | Vazifasi |
|---|---|---|
| 1 | **Backend API** (FastAPI) | Barcha biznes-logika, ma'lumotlar bazasi bilan ishlash, autentifikatsiya va ruxsatlar, tashqi tizimlarga murojaat |
| 2 | **Yuz tanish moduli** (InsightFace `buffalo_l`, ONNX Runtime, CPU) | Rasmda yuzni aniqlash, yoshni taxminlash, embedding hisoblash, ikki yuzni solishtirish |
| 3 | **Fon xizmatlari** (Celery, 3 ta) | `verify` — yuz tahlili; `storage` — rasmlarni diskka yozish, Excel yuklash, Proctoring bron; `beat` — rejali tozalash |
| 4 | **PostgreSQL** | Nomzodlar, davomat, chetlatish, foydalanuvchilar, loglar, ma'lumotnomalar |
| 5 | **Redis** | Fon vazifalari navbati, jarayon progressi, bekor qilingan tokenlar ro'yxati, kirishni bloklash hisoblagichlari |
| 6 | **Admin panel** (React) | Markaz va viloyat xodimlari uchun veb-interfeys (35 dan ortiq sahifa) |
| 7 | **Davomat Mini App** (React, Telegram ichida) | Imtihon markazi xodimlari uchun mobil interfeys |
| 8 | **Davomat boti** (aiogram) | Ruxsatni tekshirib, Mini App'ni ochish tugmasini beradi; ma'lumot bazasiga ulanmaydi |
| 9 | **Statistika boti** (aiogram) | Qabul statistikasini ko'rsatadi; ma'lumot bazasiga ulanmaydi |
| 10 | **Desktop klient** (PyQt6, alohida loyiha) | Imtihon binosida Face ID va davomat; server bilan REST orqali sinxronlanadi |

---

## 5. Tizimning asosiy obyektlari va ularning holatlari

### 5.1. Test tadbiri — holatlar ketma-ketligi

```
 [1] Yaratilgan ──► [2] Yuklab olindi ──► [3] Embedding ──► [4] Tayyor (faol) ──► [5] Yakunlangan
        ▲                 │ (nomzodlar           │ (yuz shablonlari     │ (imtihon kunlari:
        └── xatoda ───────┘  yuklanadi)          │  hisoblanadi)        │  Face ID, davomat)
            qaytariladi
```

| Holat | Nima sodir bo'ladi | Qo'shimcha ruxsat |
|---|---|---|
| 1 — Yaratilgan | Tadbir ma'lumotlari, kunlar, smenalar kiritiladi | `test_session:create/update` |
| 2 — Yuklab olindi | Fon vazifasi tashqi API'dan nomzodlarni yuklaydi; xato bo'lsa holat 1 ga qaytadi | `test_session:load_students` |
| 3 — Embedding | Fon vazifasi har nomzod pasport rasmidan embedding hisoblaydi | `test_session:embedding` |
| 4 — Tayyor | **Barcha nomzodlar tayyor bo'lsagina** o'tkaziladi; aks holda rad etiladi va sababi ko'rsatiladi («N ta nomzodda rasm yo'q», «N tasida yuz aniqlanmadi») | `test_session:update` |
| 5 — Yakunlangan | Tadbir arxiv holatida, statistika va tahlil uchun saqlanadi | `test_session:update` |

Faqat «Tayyor» holatidagi tadbirlar desktop klient va Mini App'da ko'rinadi.

### 5.2. Nomzod — belgilari

| Belgi | Ma'nosi | Kim o'rnatadi |
|---|---|---|
| `is_image` | Pasport rasmi bor | Yuklash / GTSP / qo'lda yuklash |
| `is_face` | Rasmda yuz aniqlandi, embedding hisoblandi | Embedding jarayoni |
| `is_ready` | Imtihonga tayyor (rasm + embedding) | Embedding jarayoni |
| `is_entered` | Imtihonga keldi (davomat) | Desktop, Mini App, admin |
| `is_cheating` | Chetlatilgan | Desktop, Mini App, admin |
| `is_blacklist` | Qora ro'yxatda | Chetlatish bilan birga |
| `is_applied` + `desc_apply` | To'lovni qaytarish uchun ariza bergan — **imtihonga kiritilmaydi** | Tashqi manba |
| `sp_n`, `proctoring_schedule_id` | Joy / kompyuter raqami va qaysi Proctoring sessiyasiga bog'langani | Yuklash, kompyuter biriktirish |

Muhim qoidalar:
- Chetlatilgan nomzod statistikada «Keldi» qatorida hisoblanadi (u binoga kelgan).
- Davomatdan olib tashlash faqat «keldi» belgisini o'chiradi — davomat tarixi (selfi, vaqt, ball) saqlanib qoladi.
- Bitta nomzodga bitta chetlatish yozuvi; qayta chetlatish yangi yozuv yaratmaydi.
- Qora ro'yxat faqat qo'shiladi (avtomatik ravishda o'zgartirilmaydi).

### 5.3. Davomat yozuvi (nomzod logi)
Har nomzodga bitta yozuv: birinchi va oxirgi kirish vaqti, birinchi va oxirgi selfi rasmi, o'xshashlik bali va
maksimal ball, «qo'l bilan tekshirildi» belgisi, qurilmaning IP va MAC manzili. Birinchi kirish ma'lumotlari faqat
bir marta yoziladi, keyingi kirishlarda faqat «oxirgi» maydonlar yangilanadi.

---

## 6. Ish jarayonlari (bosqichma-bosqich)

### 6.1. Jarayon 1 — Imtihonga tayyorgarlik (markaziy apparat, admin panel)

**1-qadam. Ma'lumotnomalarni tayyorlash** — viloyatlar, binolar (OTM tizimidan «Yangilash» tugmasi bilan
sinxronlanadi), testlar, smenalar, chetlatish sabablari va turlari.

**2-qadam. Test tadbirini yaratish** — test turi, nomi, raqami, boshlanish va tugash sanasi, kunlik smenalar soni.
So'ng tadbirga kun + smena juftliklari qo'shiladi.

**3-qadam. Nomzodlarni yuklash** — ikki usuldan biri:
- *Tashqi API orqali* (holatni 2 ga o'tkazish): test turiga qarab CEFR, MS, IIV yoki OTM-DTM API'si sahifalab
  o'qiladi. Har bir yozuvdan FIO, JShShIR, pasport, jins, viloyat/bino, smena, kun, guruh, joy, fan, til,
  daraja va pasport rasmi olinadi va 500 talik paketlarda bazaga yoziladi. Bino tashqi bino raqami orqali
  aniqlanadi. Mos smenasi topilmagan yoki takrorlangan yozuvlar o'tkazib yuboriladi va ro'yxati ko'rsatiladi.
  Jarayon soatlab davom etishi mumkin; kunlar bo'yicha parallel ishlaydi, foiz ko'rinishida progress
  ko'rsatiladi, bekor qilish va to'xtagan joydan davom ettirish mumkin.
- *Excel fayl orqali*: shablon yuklab olinadi, to'ldirilgan fayl yuboriladi. Majburiy ustunlar: familiya, ism,
  JShShIR, pasport seriyasi va raqami, smena raqami, imtihon sanasi, viloyat raqami. Har qator tekshiriladi,
  so'ng har nomzod uchun GTSP'dan FIO va pasport rasmi olinadi (5 ta parallel oqim).

**4-qadam. Pasport ma'lumotlarini yangilash** (zarur bo'lsa) — eskirgan pasportlar uchun:
Excel shablon (JShShIR, seriya, raqam), nusxalab qo'yilgan qatorlar, faqat JShShIR ro'yxati (seriya/raqam
E-GOV PSN'dan olinadi) yoki pasport rasmlari to'plami. Nomzod JShShIR bo'yicha topiladi.

**5-qadam. Rasmlarni to'ldirish** — rasmi yo'q nomzodlar uchun GTSP'dan yakka yoki ommaviy olish, yoki rasmni
qo'lda yuklash. Kerak bo'lsa nomzodlarni boshqa binoga ommaviy ko'chirish.

**6-qadam. Embedding hisoblash** (holatni 3 ga o'tkazish) — fon vazifasi nomzodlarni 500 tadan o'qiydi, har
pasport rasmida yuzni aniqlab embedding hisoblaydi (parallel). Natija: tayyor / rasmsiz / yuz topilmagan /
xatolik soni. Muvaffaqiyatsizlari uchun «qayta urinish» mavjud.

**7-qadam. Kompyuterlarni biriktirish** (kompyuterda o'tkaziladigan imtihonlar uchun) — kun + smena va
Proctoring'dagi ochiq sessiya tanlanadi → «Tekshirish» (sinov rejimi, hech narsa yozilmaydi) → «Biriktirish».
Qoidalar: har bino ichida ishchi kompyuterlar guruh va familiya tartibida taqsimlanadi; bir shaxsga bitta
kompyuter; Proctoring'da allaqachon bron qilingan joy saqlanadi; qayta ishga tushirish to'g'ri biriktiruvlarni
o'zgartirmaydi; joy yetmagan nomzodga «—»; ariza bergan nomzodga joy berilmaydi; Proctoring'da yo'q binoga
tegilmaydi.

**8-qadam. Faollashtirish** (holatni 4 ga o'tkazish) — tizim barcha nomzodlar tayyorligini tekshiradi. Tayyor
bo'lmasa rad etadi. Shundan so'ng tadbir desktop klient va Mini App'da paydo bo'ladi.

**9-qadam. Bino operatorlari va Mini App xodimlarini ro'yxatga olish** — admin panelda foydalanuvchilar
(bino/viloyat bilan) va davomat bot foydalanuvchilari (Telegram ID, rol, viloyatlar) yaratiladi.

### 6.2. Jarayon 2 — Imtihon kuni binoda davomat (desktop klient)

1. Operator desktop klientga login qiladi. Klient har 5 soniyada server bilan aloqani tekshiradi.
2. Klient faol test tadbirlarini oladi: operator binosi (yoki viloyati ichidagi tanlangan bino) bo'yicha
   nomzodlar soni smenalar kesimida ko'rsatiladi.
3. Klient tanlangan bino nomzodlari ro'yxatini (joy/kompyuter raqami bilan) yuklab oladi. Ariza bergan nomzodlar
   yuklanmaydi.
4. Nomzod kelganda: kamera orqali yuz olinadi, pasport rasmi bilan solishtiriladi, natija (ball) va «JOY»
   ko'rsatiladi. Zarur bo'lsa operator «qo'l bilan tekshirildi» deb belgilaydi.
5. Natija serverga darhol yuboriladi (paketda 50 tagacha yozuv; aloqa uzilsa — tiklanganda). Har yozuv
   alohida qayta ishlanadi — bittasining xatosi boshqalarini to'xtatmaydi.
6. Server: davomat yozuvini yaratadi/yangilaydi, nomzodni «keldi» deb belgilaydi.
7. Agar operator nomzodni chetlatgan bo'lsa (sabab bilan): chetlatish yozuvi, «chetlatilgan» va «qora ro'yxat»
   belgilari, qora ro'yxatga JShShIR qo'shiladi.
8. Face ID'dan o'tgan va chetlatilmagan nomzod uchun Proctoring'da kompyuter bron qilinadi (fonda, 8 martagacha
   qayta urinish; Proctoring ishlamasa ham davomat to'xtamaydi).

### 6.3. Jarayon 3 — Telegram Mini App orqali davomat (imtihon markazi xodimi)

1. Xodim davomat botiga `/start` yozadi. Bot uning Telegram ID'sini tekshiradi: ruxsat bo'lsa —
   salomlashish, biriktirilgan viloyatlar va «Davomat ilovasini ochish» tugmasi; bo'lmasa — Telegram ID'ni
   administratorga yuborish taklifi.
2. Mini App ochiladi. Bosh ekranda: xodim FIO va roli, joriy viloyat (bir nechta bo'lsa almashtirish),
   «Shaxsni tekshirish» va faol test tadbirlari ro'yxati.
3. Xodim tadbir → kun → smena tanlaydi. Smena ekranida: viloyat statistikasi, «Face ID», «Faqat tekshirish»,
   «Davomatdan olib tashlash», «Chetlatish», «Davomat statistikasi», «Davomatni guruhga yuborish»,
   «Kelmaganlar ro'yxati». Shuningdek «Kun yakuni» va «Umumiy statistika».
4. **Face ID va davomatga qo'shish:**
   1. ID-karta orqasidagi QR kod o'qiladi (ilova kamerasi, Telegram skaneri yoki rasm yuklash). Serverda
      MRZ qatoridan pasport seriya/raqami va JShShIR ajratiladi (o'qilmasa — rasm keskinlashtirilib va
      kattalashtirilib qayta uriniladi). Qo'lda kiritish ham mumkin.
   2. Xodim nomzodning selfisini oladi.
   3. Server tekshiradi:
      - tanlangan viloyat xodimga biriktirilganmi;
      - JShShIR shu smena va viloyatdami → yo'q bo'lsa, shu tadbirning boshqa kun/smena/binosidami
        («Boshqa smenada», qaysi joyda ekani ko'rsatiladi) yoki umuman yo'qmi («Topilmadi»);
      - nomzod ariza berganmi → «Imtihonga kiritilmaydi» (sababi bilan);
      - GTSP'dan pasport rasmi olinadi → javob bo'lmasa «Pasport ma'lumotlari xato»;
      - selfi pasport rasmi bilan solishtiriladi → yuz topilmasa «Yuz aniqlanmadi», aks holda ball va natija.
   4. Davomatga qo'shish faqat quyidagi holatda ruxsat etiladi: nomzod shu smenada, yuz mos keldi, ariza
      bermagan va hali qayd etilmagan. Server shu ma'lumotlar bilan **imzolangan Face ID tasdig'i** beradi
      (10 daqiqa amal qiladi, selfiga bog'langan).
   5. «Davomatga qo'shish» bosilganda server tasdiqni va selfini qayta tekshiradi, nomzodni «keldi» deb
      belgilaydi, davomat yozuvini yaratadi/yangilaydi, Proctoring bronini navbatga qo'yadi.
5. **Davomatdan olib tashlash:** JShShIR kiritiladi → shu smenadagi nomzod(lar) topiladi → tanlanadi →
   «keldi» belgisi olib tashlanadi (tarix saqlanadi).
6. **Chetlatish:** JShShIR bo'yicha butun tadbirdan nomzod topiladi → chetlatish turi va sababi tanlanadi →
   chetlatish yozuvi, qora ro'yxat (5.2-bandagi qoidalar). Allaqachon chetlatilgan bo'lsa — xabar beriladi.
7. **Shaxsni tekshirish (testga bog'lanmagan):** QR + selfi → GTSP rasmi bilan solishtirish → FIO va natija.
   Hech narsa yozilmaydi, lekin har bir so'rov audit logiga yoziladi va chastotasi cheklangan.
8. **Hisobotlar:**
   - *Davomat statistikasi* — viloyat va bino kesimida jami / keldi / kelmadi / chetlatildi, foiz,
     «100% kelgan guruhlar» (guruhdagi barcha nomzodlar kelgan bo'lsa; chetlatilgan ham kelgan hisoblanadi).
   - *Davomatni guruhga yuborish* — ayni vaqtdagi statistika bot nomidan xodim chatiga tayyor xabar bo'lib
     keladi (test nomi, sana, smena, viloyat yakuni va binolar); xodim uni guruhga forward qiladi.
     Uzun hisobot raqamlangan qismlarga bo'linadi.
   - *Kelmaganlar ro'yxati* — Excel fayl bot orqali xodim chatiga yuboriladi.

### 6.4. Jarayon 4 — Monitoring va hisobotlar (admin panel)

1. **Test dashboard** — faol tadbirlar bo'yicha umumiy ko'rsatkichlar, kunlar bo'yicha kelganlar grafigi.
2. **Statistika** — tanlangan tadbir bo'yicha smena / kun / umumiy kesimda viloyatlar jadvali (jami, keldi,
   kelmadi, chetlatildi, foiz); viloyat bosilganda binolar va «100% kelgan guruhlar» oynasi. Excel'ga eksport:
   davomat statistikasi, kelmaganlar ro'yxati.
3. **Nomzodlar** — qidiruv va filtrlar (tadbir, smena, viloyat, bino, keldi/kelmadi, chetlatilgan,
   qora ro'yxat, tayyorlik), nomzod kartasi, Excel/PDF eksport.
4. **Davomat loglari** — kim, qachon kirdi, selfi rasmlari, ball, qurilma; tahrirlash va o'chirish (ruxsat bilan).
5. **Chetlatilganlar** — sabab, kim chetlatgan, rasm; Excel eksport.
6. **Kelgan / kelmagan / ariza bergan / rad etilganlar** ro'yxatlari (viloyat doirasida).
7. Viloyat xodimi barcha sahifalarda faqat o'z viloyati ma'lumotlarini ko'radi.

### 6.5. Jarayon 5 — Imtihondan keyingi natija tahlili

1. Tahlilchi tadbir, kunlar oralig'i va smenani tanlaydi, tashqi natija tizimidan olingan qatorlarni joylaydi.
2. Tizim ularni JShShIR bo'yicha FaceID bazasi bilan solishtiradi va uchta toifadan birini chiqaradi:
   - «Faceda bor — chetlatilmagan — natija chiqmagan»;
   - «Faceda bor — chetlatilgan — natija chiqqan» (chetlatilgan bo'lsa ham natija chiqqan);
   - «Faceda yo'q — natija chiqqan» (davomatda yo'q shaxsga natija chiqqan).
3. Natija jadval (rasm havolalari bilan) va Excel ko'rinishida beriladi.
4. Tahlil yakunlangach tadbir «Yakunlangan» holatiga o'tkaziladi.

### 6.6. Jarayon 6 — Tashqi tizimlar uchun rasm tekshirish xizmati

**Rasm sifatini tekshirish** (masalan, sertifikat uchun rasm qabul qilishda):
1. Tashqi tizim API kalit bilan base64 rasm va nomzod yoshini yuboradi.
2. Navbat to'lgan bo'lsa — «keyinroq urining» (429 va kutish vaqti) javobi; aks holda vazifa raqami qaytadi.
3. Fon xizmati rasmni tekshiradi: yuz bormi; taxminiy yosh ±10 yil ichidami; o'lcham 200–500 × 250–600 piksel
   oralig'idami; orqa fon yetarlicha ochiqmi (burchaklar o'rtacha rangi); rang palitrasi.
4. Tashqi tizim vazifa raqami bo'yicha natijani so'raydi: yaroqli/yaroqsiz va xatoliklar ro'yxati.
5. Rasm WebP ko'rinishida saqlanadi, tekshiruv logga yoziladi (admin panel — «Tekshiruv loglari»).

**Ikki yuzni solishtirish:** pasport rasmi va jonli rasm yuboriladi → har ikkisida yuz aniqlanadi →
embeddinglar kosinus o'xshashligi hisoblanadi → ball va «mos keldi / mos kelmadi» natijasi
(chegara sozlamada: 0,45). Rasmlar va natija logga yoziladi («Yuz solishtirish loglari»).

**Embedding olish:** rasmdan embedding vektori sinxron qaytariladi.

Admin panelda xuddi shu funksiyalar «Rasm tekshirish» va «Yuzlarni solishtirish» sahifalarida qo'lda ham bajariladi.

### 6.7. Jarayon 7 — Pasport ma'lumotlarini olish

Vakolatli xodim pasport seriyasi, raqami va JShShIR'ni kiritadi → GTSP'dan FIO, jins, tug'ilgan sana va joy,
fuqarolik, hayotiylik holati va pasport rasmi ko'rsatiladi. Admin panelda nomzod uchun «GTSP bilan Face ID
tekshiruvi» ham mavjud: kamera rasmi GTSP rasmi bilan solishtiriladi (avval nomzod tanlangan smena va
binodaligi tekshiriladi), bazaga hech narsa yozilmaydi.

### 6.8. Jarayon 8 — Qabul statistikasi

1. Statistika boti foydalanuvchisi `/start`, «📊 Statistika» yoki «🔄 Yangilash» buyrug'ini beradi.
2. Bot backend'dan foydalanuvchining Telegram ID'si bo'yicha ruxsatini va darajasini tekshiradi.
3. Backend tashqi qabul statistikasi API'sidan ma'lumot oladi (60 soniya kesh) va viloyatlar kesimida
   arizalar soni, jins bo'yicha, to'lov holati, o'tgan yil bilan taqqoslashni qaytaradi.
4. Bot darajaga ko'ra ma'lumotni cheklab ko'rsatadi. Admin panelda «Qabul» sahifasi xuddi shu ma'lumotni beradi.

### 6.9. Jarayon 9 — Kirish huquqlarini boshqarish

1. **Rollar va ruxsatlar:** administrator rol yaratadi va unga ruxsat kodlarini belgilaydi. Ruxsatlar katalogi
   har server ishga tushganda avtomatik yangilanadi (yangi ruxsatlar administratorga beriladi, eskirganlari
   o'chiriladi).
2. **Foydalanuvchilar:** login, parol (kamida 8 belgi, katta va kichik harf, raqam), FIO, rol, viloyat, bino,
   Telegram ID, faol/bloklangan holati.
3. **API kalitlar:** nom bilan yaratiladi, to'liq kalit faqat bir marta ko'rsatiladi; oxirgi ishlatilgan vaqti
   kuzatiladi; bekor qilish mumkin.
4. **Bot foydalanuvchilari:** davomat (rol + viloyatlar) va statistika (daraja) foydalanuvchilarini qo'shish,
   tahrirlash, bloklash.
5. **Audit:** muvaffaqiyatsiz kirish urinishlari (login, IP, brauzer, sabab, vaqt) — 90 kun saqlanadi;
   onlayn foydalanuvchilar (faol login sessiyalari).

### 6.10. Jarayon 10 — Tizimga kirish va sessiya

1. Foydalanuvchi login va parol kiritadi.
2. Server tekshiradi: login bloklanmaganmi (15 daqiqada 5 xato → 15 daqiqa bloklash); parol to'g'rimi;
   foydalanuvchi faolmi. Har xato urinish audit jurnaliga yoziladi.
3. Muvaffaqiyatli bo'lsa: qisqa muddatli kirish tokeni (administrator uchun 60 daqiqa) va uzoq muddatli
   yangilash tokeni (faqat server o'qiy oladigan cookie'da) beriladi.
4. Kirish tokeni muddati tugaganda brauzer avtomatik yangilaydi; har yangilashda yangilash tokeni almashadi,
   eski token qayta ishlatilsa butun sessiya oilasi bekor qilinadi.
5. «Chiqish» — yangilash tokeni bekor qilinadi, kirish tokeni darhol yaroqsiz ro'yxatiga qo'shiladi.
6. Sahifalar va tugmalar foydalanuvchi ruxsatlariga qarab ko'rsatiladi.

### 6.11. Jarayon 11 — Fon va xizmat jarayonlari

| Jarayon | Davriyligi | Vazifasi |
|---|---|---|
| Nomzodlarni yuklash | Talab bo'yicha | Tashqi API'dan (8 soatgacha) |
| Excel'dan yuklash + GTSP | Talab bo'yicha | 1 soatgacha |
| Embedding hisoblash / qayta urinish | Talab bo'yicha | Pasport rasmlaridan yuz shablonlari |
| Rasm tekshirish, yuz solishtirish | Har so'rovda | Navbat orqali |
| Rasmlarni diskka saqlash | Har tekshiruvda | WebP formatida |
| Proctoring bron | Har davomatda | 8 martagacha qayta urinish (10 s → 300 s) |
| Eskirgan yangilash tokenlarini tozalash | Har soatda | — |
| Eski kirish urinishlarini tozalash | Har kuni | 90 kundan eskilari |
| Server holatini tekshirish (health) | Desktop klientlardan har 5 s | Autentifikatsiyasiz |

---

## 7. Tizim funksiyalarining to'liq ro'yxati (modullar bo'yicha)

### 7.1. Admin panel sahifalari

| № | Sahifa | Funksiyalar | Ruxsat |
|---|---|---|---|
| 1 | Kirish | Login/parol bilan kirish | — |
| 2 | Dashboard | Rasm tekshiruv va yuz solishtirish statistikasi | `dashboard:read`, `dashboard:stats` |
| 3 | Test dashboard | Faol tadbirlar umumiy ko'rsatkichlari, kunlik kelganlar | `dashboard:read` / `test_session:read` |
| 4 | Test tadbirlari | Ro'yxat, yaratish, tahrirlash, o'chirish, smenalar | `test_session:*` |
| 5 | Test tadbiri sahifasi | Holatni o'zgartirish, yuklash/embedding progressi, bekor qilish, qayta yuklash, Excel yuklash, pasport yangilash (4 usul), kompyuter biriktirish, nomzodlar statistikasi | `test_session:*`, `load_students`, `embedding`, `cancel_process`, `assign_seats` |
| 6 | Statistika | Smena/kun/umumiy davomat, viloyat → binolar, 100% kelgan guruhlar, Excel eksport, kelmaganlar | `statistics:read/export/absentees` |
| 7 | Nomzodlar | Qidiruv, filtr, kartochka, tahrirlash, o'chirish, rasm yuklash, GTSP'dan olish (yakka/ommaviy), binoga ko'chirish, davomatdan olib tashlash, Excel/PDF eksport | `student:*` |
| 8 | Davomat loglari | Ro'yxat, selfi rasmlari, tahrirlash, o'chirish | `student_log:*` |
| 9 | Chetlatilganlar | Ro'yxat, qo'shish, tahrirlash, o'chirish, Excel eksport | `cheating_log:*` |
| 10 | Natija tahlili | 3 rejimdagi solishtirish, Excel | `result_analysis:read` |
| 11 | Rasm tekshirish | Rasm yuklab sifatini tekshirish | `photo:verify` |
| 12 | Yuzlarni solishtirish | Ikki rasmni solishtirish | `photo:verify_two_face` |
| 13 | Embedding | Rasmdan embedding olish | `embedding:extract` |
| 14 | Pasport ma'lumoti | GTSP'dan shaxs ma'lumoti | `pasport_info:read` |
| 15 | Tekshiruv loglari | Rasm tekshiruvlari tarixi va rasmlari | `log:read` |
| 16 | Yuz solishtirish loglari | Solishtiruvlar tarixi, ikkala rasm | `face_log:read` |
| 17 | Foydalanuvchilar | CRUD, bloklash | `user:*` |
| 18 | Onlayn foydalanuvchilar | Faol sessiyalar | `online_users:read` |
| 19 | Rollar | CRUD | `role:*` |
| 20 | Rol ruxsatlari | Rolga ruxsat biriktirish | `role:update`, `permission:*` |
| 21 | API kalitlar | Yaratish, ro'yxat, bekor qilish | `api_key:*` |
| 22 | Muvaffaqiyatsiz kirishlar | Audit jurnali | `failed_login:read` |
| 23 | Davomat bot foydalanuvchilari | CRUD, rol, viloyatlar | `davomat_bot:*` |
| 24 | Statistika bot foydalanuvchilari | CRUD, daraja | `statistic_bot:*` |
| 25 | Qabul | Qabul statistikasi | `qabul:read` |
| 26–35 | Sozlamalar: Viloyatlar, Binolar (+OTM sinxronlash), Testlar, Smenalar, Sessiya holatlari, Chetlatish sabablari, Chetlatish turlari, Jinslar, Qora ro'yxat | CRUD | tegishli `<bo'lim>:*` |

### 7.2. Telegram Mini App ekranlari

| Ekran | Funksiyalar |
|---|---|
| Bosh ekran | Xodim profili, viloyatni tanlash, «Shaxsni tekshirish», faol tadbirlar |
| Test tadbiri | Kunlar va smenalar, «Kun yakuni», «Umumiy statistika» |
| Smena | Viloyat statistikasi, Face ID, Faqat tekshirish, Davomatdan olib tashlash, Chetlatish, hisobotlar |
| Face ID | QR o'qish (3 usul) yoki qo'lda kiritish, selfi, natija, davomatga qo'shish |
| Davomatdan olib tashlash | JShShIR → nomzodni tanlash → tasdiqlash |
| Chetlatish | JShShIR → nomzod → tur va sabab → tasdiqlash |
| Statistika / Viloyat | Viloyat va binolar kesimi, 100% kelgan guruhlar |

### 7.3. Telegram botlar
- **Davomat boti:** `/start`, `/menu` — ruxsat tekshiruvi va Mini App tugmasi; chat menyusidagi «Davomat» tugmasi;
  eski tugmalar va boshqa xabarlarga Mini App'ga yo'naltirish; kelmaganlar Excel'i va davomat hisobotini chatga yuborish.
- **Statistika boti:** `/start`, `/stat`, `/refresh` — qabul statistikasi.

### 7.4. Tashqi API (tashqi tizimlar uchun, `API_DOCS.md`)
Rasm tekshirish (yuborish + natija), ikki yuzni solishtirish (yuborish + natija), embedding olish.

---

## 8. Tashqi tizimlar bilan o'zaro aloqa

| Tizim | Yo'nalish | Qachon | Uzatiladigan ma'lumot |
|---|---|---|---|
| GTSP | Tizim → GTSP | Excel yuklash, rasm to'ldirish, Face ID (Mini App, admin), pasport ma'lumoti | So'rov: pasport seriya+raqam, JShShIR. Javob: FIO, jins, tug'ilgan sana/joy, fuqarolik, pasport rasmi |
| E-GOV PSN | Tizim → E-GOV | Pasport yangilash (JShShIR ro'yxati bo'yicha) | So'rov: JShShIR. Javob: joriy pasport seriya/raqami |
| CEFR, MS, IIV, OTM-DTM API | Tizim → tashqi | Nomzodlarni yuklash | Javob: nomzodlar ro'yxati va pasport rasmlari |
| OTM binolari API | Tizim → tashqi | Binolarni sinxronlash | Javob: binolar ro'yxati |
| Proctoring | Tizim → Proctoring | Kompyuter biriktirish, davomatdan keyin bron | Sessiyalar, kompyuterlar; nomzod JShShIR va kompyuter raqami |
| Telegram Bot API | Tizim → Telegram | Mini App hisobotlari | Excel fayl, statistika xabari |
| Qabul statistikasi API | Tizim → tashqi | Statistika bot, «Qabul» sahifasi | Viloyatlar bo'yicha qabul ko'rsatkichlari |
| Natija tizimi rasm bazasi | Brauzer → tashqi | Natija tahlili | Rasm havolalari |
| Tashqi axborot tizimlari | Tashqi → Tizim | Rasm tekshirish xizmati | Rasmlar (base64), yosh |
| Telegram (Mini App) | Telegram → Tizim | Har so'rovda | Telegram imzolagan foydalanuvchi ma'lumoti |

Tashqi tizim sozlanmagan bo'lsa tegishli funksiya «xizmat mavjud emas» (503) javobini qaytaradi; Proctoring
bron esa jimgina o'tkazib yuboriladi (davomat to'xtamaydi).

---

## 9. Qayta ishlanadigan ma'lumotlar

| Ma'lumot | Qayerda | Toifa |
|---|---|---|
| Pasport rasmi | Baza (nomzod pasport ma'lumotlari) | **Biometrik** |
| Yuz embeddingi | Baza | **Biometrik shablon** |
| Imtihon kunidagi selfi rasmlari | Baza (davomat yozuvi) | **Biometrik** |
| Tekshiruv va solishtirish rasmlari | Server diski (`uploads/`, WebP) | **Biometrik** |
| FIO, JShShIR, pasport seriya/raqami, jins, telefon | Baza | Shaxsga doir |
| Imtihon joyi, smena, guruh, fan, til, daraja | Baza | Xizmat ma'lumoti |
| Davomat, chetlatish, qora ro'yxat | Baza | Shaxsga doir, yuridik ahamiyatli |
| Operator qurilmasi IP va MAC manzili | Baza | Texnik |
| Foydalanuvchi parollari | Baza (bcrypt xesh) | Maxfiy |
| Yangilash tokenlari, API kalitlar | Baza (xesh ko'rinishida) | Maxfiy |
| Kirish urinishlari (login, IP, brauzer) | Baza | Audit |
| Bot foydalanuvchilari (FIO, Telegram ID) | Baza | Shaxsga doir |
| Server sirlari (imzo kalitlari, bot tokenlari, tashqi API tokenlari, baza paroli) | Serverdagi `.env` fayllar | **Kritik** |

---

## 10. Tizimdagi xavfsizlik mexanizmlari

| Soha | Qo'llanilgan choralar |
|---|---|
| Parollar | bcrypt (cost 12); murakkablik siyosati; login mavjudligini javob vaqti orqali aniqlashdan himoya |
| Kirishni bloklash | 15 daqiqada 5 xato urinish → 15 daqiqa bloklash; har xato urinish jurnalga yoziladi |
| Sessiyalar | Qisqa muddatli imzolangan kirish tokeni (JWT, majburiy `exp/iat/iss/sub/jti`); yangilash tokeni HttpOnly + Secure + SameSite cookie'da; har yangilashda almashtirish, qayta ishlatilsa butun oila bekor; chiqishda token darhol bekor |
| CSRF | Double-submit cookie (token yangilash va chiqishda) |
| API kalitlar | 48 baytli tasodifiy kalit; bazada server sirli HMAC-SHA256 xesh; bir vaqtda ikki xil autentifikatsiya taqiqlangan |
| Mini App | Har so'rovda Telegram imzosi (HMAC) bot tokeni bilan tekshiriladi, 24 soat muddat; foydalanuvchi bloklansa — keyingi so'rovdayoq rad; davomatga faqat server imzolagan Face ID tasdig'i bilan qo'shiladi |
| Ruxsatlar | 101 ta ruxsat kodi; har endpointda tekshiruv; viloyat doirasi alohida tekshiriladi; Mini App'da har so'rovdagi viloyat xodimga biriktirilganligi tekshiriladi |
| So'rovlar chastotasi | Foydalanuvchi/kalit/Telegram ID/IP bo'yicha chegaralar (login 50/daq, Face ID 30/daq, Excel yuborish 10/daq va h.k.); yuz tahlili navbati to'lganda 429 |
| HTTP sarlavhalari | HSTS, `nosniff`, `X-Frame-Options: DENY`, qat'iy CSP, Referrer-Policy, Permissions-Policy; CORS — aniq domenlar |
| Konfiguratsiya | Zaif yoki namunaviy imzo kalitlari bilan server ishga tushmaydi |
| Loglar | Har so'rovga identifikator; loglarda bot tokeni yashiriladi; monitoring metrikalari token bilan himoyalangan |
| Kiruvchi ma'lumot | Rasm hajmi (5 MB) va o'lchami (4096 px) chegaralari; ma'lumotlar sxema bo'yicha tekshiriladi; SQL so'rovlari parametrlangan (ORM); bazada so'rov vaqti chegarasi 60 s |
| Fon xizmatlari | Navbatda faqat JSON formatdagi vazifalar |

---

## 11. Texnik ta'minot va joylashtirish muhiti

| Qatlam | Texnologiya |
|---|---|
| Backend | Python 3, FastAPI 0.115, SQLAlchemy 2.0, Pydantic 2, Alembic, gunicorn + uvicorn (8 worker, unix socket) |
| Yuz tanish | InsightFace 0.7.3 (`buffalo_l`), ONNX Runtime 1.20 (CPU), OpenCV 4.10, zxing-cpp 2.2 (QR) |
| Fon xizmatlari | Celery 5.4 (3 xizmat: verify, storage, beat), Redis 7 |
| Ma'lumotlar bazasi | PostgreSQL 16 |
| Frontend | React 18, TypeScript, Vite, Tailwind (admin panel va Mini App) |
| Botlar | aiogram 3.13, aiohttp 3.10 (long polling) |
| Desktop klient | PyQt6 (alohida loyiha) |
| Server | Linux, nginx (HTTPS, statik fayllar, so'rov hajmi 10 MB), systemd xizmatlari, `/var/www/faceid_davomat` |
| Hujjatlar | `CLAUDE.md`, `API_DOCS.md`, `deploy/DAVOMAT_MINIAPP.md`, `backend/SECURITY_MIGRATION.md`, foydalanuvchi qo'llanmasi (`docs/`) |

---

## 12. Ekspertizaga qo'yiladigan talablar

### 12.1. Ekspertiza obyekti
Backend API (A ilovadagi barcha endpointlar), admin panel, Telegram Mini App, davomat va statistika botlari,
fon xizmatlari, ma'lumotlar bazasi, server infratuzilmasi, manba kodi va bog'liqliklar, yuz tanish moduli,
tashqi tizimlar bilan aloqa. Desktop klient — buyurtmachi qaroriga ko'ra alohida.
Tashqi davlat tizimlarining o'zi (GTSP, E-GOV va boshq.) va Telegram platformasi ekspertiza obyektiga kirmaydi.

### 12.2. Tekshirilishi kerak bo'lgan yo'nalishlar
1. Autentifikatsiya va sessiyalarni boshqarish (6.10-jarayon).
2. Ruxsatlar va viloyat doirasi — har bir funksiyada (7-bo'lim, B ilova); boshqa viloyat ma'lumotiga kirish imkoniyati.
3. Davomatni soxtalashtirish imkoniyati — desktop, Mini App, bot va admin kanallari orqali (6.2, 6.3).
4. Face ID'ni aldash (foto, ekran, niqob) va solishtirish chegarasining ishonchliligi.
5. Biometrik va shaxsga doir ma'lumotlarning sizib chiqishi — eksportlar, rasmlar, loglar, zaxira nusxalar.
6. GTSP va E-GOV orqali pasport ma'lumotlarini ruxsatsiz yoki ommaviy olish imkoniyati.
7. Bot tokeni va API kalitlarining saqlanishi va sizib chiqqandagi ta'siri.
8. Fayl yuklash (Excel, rasmlar, QR) va eksport fayllari xavfsizligi.
9. Imtihon kuni ish qobiliyatini saqlash (og'ir funksiyalar, navbatlar, chastota chegaralari).
10. Server, nginx, PostgreSQL, Redis konfiguratsiyasi va tarmoq perimetri.
11. Bog'liqliklardagi ma'lum zaifliklar va manba kodi hamda git tarixidagi sirlar.
12. Shaxsga doir ma'lumotlar to'g'risidagi qonunchilik talablariga muvofiqlik.

### 12.3. Shartlar
- Faol tekshiruvlar prod nusxasi bo'lgan, sun'iy ma'lumotli test muhitida o'tkaziladi.
- Imtihon kunlarida prod muhitda faol tekshiruv o'tkazilmaydi (jadval buyurtmachi tomonidan beriladi).
- Ekspertga har rol uchun test akkauntlari, test API kalitlari, test Telegram boti va manba kodi beriladi.
- Olingan shaxsga doir ma'lumotlar maxfiy saqlanadi va ekspertizadan so'ng yo'q qilinadi; maxfiylik
  kelishuvi imzolanadi.
- Kritik zaiflik aniqlansa, buyurtmachi 24 soat ichida xabardor qilinadi.

### 12.4. Natija
Topilmalar ro'yxati (xavf darajasi, CVSS, takrorlash bosqichlari, tavsiya), xulosa va bartaraf etilgandan
so'ng qayta tekshiruv natijalari.

---

## Ilova A. API endpointlar ro'yxati

Barcha yo'llar `/api/v1` prefiksi bilan (jami 190 ga yaqin).

| Bo'lim | Endpointlar | Kirish |
|---|---|---|
| Xizmat | `GET /health`, `/healthcheck` (+ ildizda `/health`), ildizda `/metrics` | ochiq / metrika tokeni |
| Kirish | `POST /auth/login`, `/auth/refresh`, `/auth/logout`; `GET /auth/me` | — / cookie + CSRF / JWT |
| Rasm xizmati | `POST /photo/verify-photo`, `GET /photo/verify-photo/status/{task_id}`, `POST /photo/verify-two-face`, `GET /photo/verify-two-face/status/{task_id}`, `POST /embedding/extract` | JWT / API kalit + ruxsat |
| Pasport | `POST /pasport-info` | `pasport_info:read` |
| Administrlash | `/admin/logs[/{id}[/image]]`, `/admin/stats`, `/admin/face-stats`, `/admin/users[/{id}]`, `/admin/face-logs[/{id}[/image/{img_type}]]`, `/admin/api-keys[/{id}]`, `/admin/failed-logins[/count]`, `/admin/online-users`, `/admin/davomat-bots[/{id}]`, `/admin/statistic-bots[/{id}]` | tegishli ruxsatlar |
| Ruxsatlar | `GET /permissions/catalog` (ochiq), `/permissions[/{id}]`, `/permissions/roles[/{role_id}]` | `permission:*`, `role:*` |
| Test tadbirlari | `/test-sessions` (ro'yxat, yaratish), `/{id}` (ko'rish, tahrirlash, o'chirish), `/{id}/state`, `/{id}/smenas[/{smena_id}]`, `/{id}/students`, `/{id}/student-stats`, `/{id}/upload-excel`, `/{id}/passport-update[/excel|/images|/psn]`, `/{id}/student-load-progress`, `/{id}/cancel-student-load`, `/{id}/reload-student-load`, `/{id}/embedding-progress`, `/{id}/retry-embedding`, `/{id}/dashboard-stats[/regions/{region_id}/full-groups|/export|/absentees-export]`, `/active`, `/tests`, `/smenas`, `/states`, `/excel-template`, `/passport-template`, `/dashboard-overview`, `/dashboard-daily-entered`, `/smenas/{smena_id}/attendance-stats`, `/smenas/{smena_id}/attendance-by-region` | `test_session:*`, `statistics:*` |
| Kompyuter biriktirish | `GET /proctoring/schedules`, `GET /test-sessions/{id}/seat-assignment`, `POST /test-sessions/{id}/assign-seats` | `test_session:assign_seats` |
| Nomzodlar | `/students` (ro'yxat, yaratish), `/students/export`, `/students/{id}` (ko'rish, tahrirlash, o'chirish), `/{id}/upload-image`, `/{id}/fetch-gtsp`, `/fetch-gtsp-bulk`, `/reassign-zone-bulk`, `/{id}/remove-attendance`, `/applied`, `/not-entered`, `/not-entered-grouped`, `/entered`, `/rejected`, `/check-faceid-gtsp`, `/check-faceid-gtsp-self` | `student:*` + viloyat doirasi |
| Davomat loglari | `/students/logs[/{id}]`, `POST /students/logs/bulk` (desktop) | `student_log:*` |
| Chetlatish | `/students/cheating-logs[/{id}]`, `/students/cheating-logs/export` | `cheating_log:*` |
| Ma'lumotnomalar | `/lookup/{tests,smenas,session-states,regions,zones,roles,reasons,reason-types,blacklist,genders}[/{id}]`, `/lookup/zones/my-region`, `POST /lookup/zones/sync-from-otm` | `<bo'lim>:*` |
| Natija tahlili | `GET /result-analysis/config`, `/sessions`; `POST /result-analysis/analyze`, `/export` | `result_analysis:read` |
| Davomat boti | `/davomat-bot/check/{telegram_id}`, `/ready-sessions`, `/sessions/{id}/stats`, `/sessions/{id}/absentees.xlsx`, `/face-verify`, `/mark-attendance`, `/find-by-jshshir`, `/remove-attendance`, `/reason-types`, `/reasons`, `/find-for-cheat`, `/cheating` | bot API kaliti + Telegram ID |
| Mini App | `/davomat-miniapp/me`, `/sessions`, `/sessions/{id}/stats`, `/sessions/{id}/absentees/send`, `/sessions/{id}/stats/send`, `/passport-qr`, `/face-verify`, `/face-check`, `/mark-attendance`, `/find-by-jshshir`, `/remove-attendance`, `/reason-types`, `/reasons`, `/find-for-cheat`, `/cheating` | Telegram imzosi |
| Statistika boti | `/statistic-bot/check/{telegram_id}`, `/statistics`, `/qabul` | bot API kaliti / `qabul:read` |

---

## Ilova B. Ruxsatlar katalogi (101 ta)

| Guruh | Ruxsatlar |
|---|---|
| Dashboard | `dashboard:read` — ko'rish; `dashboard:stats` — statistika |
| Rasm xizmati | `photo:verify` — rasm tekshirish; `photo:verify_two_face` — yuz solishtirish; `embedding:extract` — embedding olish |
| Loglar | `log:read`, `log:delete` — tekshiruv loglari; `face_log:read`, `face_log:delete` — solishtirish loglari |
| API kalitlar | `api_key:read`, `api_key:create`, `api_key:delete` |
| Foydalanuvchilar | `user:read`, `user:create`, `user:update`, `user:delete`; `online_users:read` |
| Rollar va ruxsatlar | `role:read/create/update/delete`; `permission:read/create/update/delete` |
| Test tadbirlari | `test_session:read/create/update/delete`; `load_students` — yuklashni boshlash; `embedding` — embeddingni boshlash; `cancel_process` — jarayonni bekor qilish; `assign_seats` — kompyuter biriktirish |
| Nomzodlar | `student:read/create/update/delete`; `all_regions` — barcha viloyatlar; `fetch_gtsp` — GTSP'dan olish; `export_excel`, `export_pdf` — eksport |
| Davomat loglari | `student_log:read/create/update/delete` (`create` — desktop sinxronlash ham) |
| Chetlatish | `cheating_log:read/create/update/delete/export` |
| Ma'lumotnomalar | `region`, `zone`, `test`, `smena`, `session_state`, `reason`, `reason_type`, `gender`, `blacklist` — har biri `:read/create/update/delete` |
| Audit | `failed_login:read` |
| Statistika | `statistics:read`, `statistics:export`, `statistics:absentees` |
| Pasport | `pasport_info:read` |
| Bot foydalanuvchilari | `davomat_bot:read/create/update/delete`; `statistic_bot:read/create/update/delete` |
| Qabul | `qabul:read` |
| Natija tahlili | `result_analysis:read` |
