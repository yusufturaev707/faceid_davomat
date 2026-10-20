# FaceID API — Tashqi tizimlar uchun dokumentatsiya

## Autentifikatsiya

Barcha so'rovlarda `X-API-Key` header yuborilishi shart.
API kalitni admin paneldan olasiz.

```
X-API-Key: sk-xxxx...
```

---

## 1. Rasm tekshirish (verify-photo)

ID rasm sifatiga tekshiradi: yuz aniqlash, yosh, o'lcham, orqa fon, palitra.

### 1.1 Rasmni yuborish

```
POST /api/v1/photo/verify-photo
```

**Headers:**
```
Content-Type: application/json
X-API-Key: sk-xxxx...
```

**Body:**
```json
{
  "img_b64": "data:image/jpeg;base64,/9j/4AAQ... yoki sof base64",
  "age": 25
}
```

| Field | Tur | Tavsif |
|---|---|---|
| `img_b64` | string | Rasm base64 formatda (max 5MB) |
| `age` | integer | Foydalanuvchi yoshi (1-120) |

**Response (202):**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### 1.2 Natijani olish

`task_id` orqali natijani so'rash. Status `SUCCESS` yoki `FAILURE` bo'lguncha 1-2 soniya oraliqda polling qiling.

```
GET /api/v1/photo/verify-photo/status/{task_id}
```

**Headers:**
```
X-API-Key: sk-xxxx...
```

**Response — kutilmoqda:**
```json
{
  "task_id": "a1b2c3d4...",
  "status": "PENDING",
  "result": null,
  "error": null
}
```

**Response — muvaffaqiyatli:**
```json
{
  "task_id": "a1b2c3d4...",
  "status": "SUCCESS",
  "result": {
    "success": true,
    "detection": true,
    "back_color": [245, 243, 240],
    "size": {
      "width": 354,
      "height": 472
    },
    "palitra_rgb": {
      "min_palitra": [12, 8, 5],
      "max_palitra": [255, 255, 253]
    },
    "file_size_byte": 45230,
    "error_messages": []
  },
  "error": null
}
```

**Response — rad etilgan rasm:**
```json
{
  "task_id": "a1b2c3d4...",
  "status": "SUCCESS",
  "result": {
    "success": false,
    "detection": true,
    "back_color": [120, 98, 85],
    "size": {
      "width": 640,
      "height": 480
    },
    "palitra_rgb": {
      "min_palitra": [0, 0, 0],
      "max_palitra": [255, 255, 255]
    },
    "file_size_byte": 82400,
    "error_messages": [
      "O'lcham noto'g'ri: 640x480, talab: 200-500 x 250-600",
      "Orqa fon juda qorong'i: RGB(120, 98, 85)"
    ]
  },
  "error": null
}
```

**Response — xatolik:**
```json
{
  "task_id": "a1b2c3d4...",
  "status": "FAILURE",
  "result": null,
  "error": "Base64 dekodlash xatosi: yaroqsiz format"
}
```

### Result fieldlari

| Field | Tur | Tavsif |
|---|---|---|
| `success` | boolean | `true` — rasm barcha tekshiruvlardan o'tdi |
| `detection` | boolean | Rasmda yuz aniqlangan yoki yo'q |
| `back_color` | [R, G, B] | Orqa fon rangi (4 burchak o'rtachasi) |
| `size` | object | Rasm o'lchamlari (width, height) |
| `palitra_rgb` | object | Rasm palitrasining min/max RGB qiymatlari |
| `file_size_byte` | number | Fayl hajmi baytlarda |
| `error_messages` | string[] | Rad etilish sabablari (bo'sh massiv = muvaffaqiyatli) |

---

## 2. Ikki yuzni solishtirish (verify-face)

Pasport rasmi va jonli rasmni solishtiradi. Bir xil odam ekanligini aniqlaydi.

### 2.1 Rasmlarni yuborish

```
POST /api/v1/photo/verify-two-face
```

**Headers:**
```
Content-Type: application/json
X-API-Key: sk-xxxx...
```

**Body:**
```json
{
  "ps_img": "base64 pasport rasmi...",
  "lv_img": "base64 jonli rasm..."
}
```

| Field | Tur | Tavsif |
|---|---|---|
| `ps_img` | string | Pasport rasmi base64 formatda (max 5MB) |
| `lv_img` | string | Jonli (live) rasm base64 formatda (max 5MB) |

**Response (202):**
```json
{
  "task_id": "f7e8d9c0-b1a2-3456-7890-abcdef123456"
}
```

### 2.2 Natijani olish

```
GET /api/v1/photo/verify-two-face/status/{task_id}
```

**Headers:**
```
X-API-Key: sk-xxxx...
```

**Response — muvaffaqiyatli:**
```json
{
  "task_id": "f7e8d9c0...",
  "status": "SUCCESS",
  "result": {
    "score": 0.7234,
    "thresh_score": 0.45,
    "verified": true,
    "message": "Yuzlar mos keldi (ball: 0.7234)",
    "ps_detection": true,
    "lv_detection": true,
    "ps_file_size": 45230,
    "lv_file_size": 62100,
    "ps_width": 354,
    "ps_height": 472,
    "lv_width": 640,
    "lv_height": 480,
    "error_messages": []
  },
  "error": null
}
```

**Response — yuzlar mos kelmadi:**
```json
{
  "task_id": "f7e8d9c0...",
  "status": "SUCCESS",
  "result": {
    "score": 0.2145,
    "thresh_score": 0.45,
    "verified": false,
    "message": "Yuzlar mos kelmadi (ball: 0.2145, chegara: 0.45)",
    "ps_detection": true,
    "lv_detection": true,
    "ps_file_size": 45230,
    "lv_file_size": 62100,
    "ps_width": 354,
    "ps_height": 472,
    "lv_width": 640,
    "lv_height": 480,
    "error_messages": []
  },
  "error": null
}
```

**Response — yuz aniqlanmadi:**
```json
{
  "task_id": "f7e8d9c0...",
  "status": "SUCCESS",
  "result": {
    "score": 0.0,
    "thresh_score": 0.45,
    "verified": false,
    "message": "Yuz aniqlanmadi",
    "ps_detection": true,
    "lv_detection": false,
    "ps_file_size": 45230,
    "lv_file_size": 62100,
    "ps_width": 354,
    "ps_height": 472,
    "lv_width": 640,
    "lv_height": 480,
    "error_messages": ["Jonli rasmda yuz aniqlanmadi"]
  },
  "error": null
}
```

### Result fieldlari

| Field | Tur | Tavsif |
|---|---|---|
| `score` | float | O'xshashlik balli (0.0 — 1.0) |
| `thresh_score` | float | Chegara qiymati (hozir: 0.45) |
| `verified` | boolean | `true` — yuzlar bir xil odam |
| `message` | string | Natija xabari |
| `ps_detection` | boolean | Pasport rasmida yuz aniqlandi |
| `lv_detection` | boolean | Jonli rasmda yuz aniqlandi |
| `ps_file_size` | integer | Pasport rasm hajmi (bayt) |
| `lv_file_size` | integer | Jonli rasm hajmi (bayt) |
| `ps_width`, `ps_height` | integer | Pasport rasm o'lchamlari |
| `lv_width`, `lv_height` | integer | Jonli rasm o'lchamlari |
| `error_messages` | string[] | Xatolik xabarlari |

---

## 3. Davomat holati (keldi / kelmadi)

Imtihonga nomzod kelgan-kelmaganini olish. Faqat o'qish — tizimda hech narsa
o'zgartirilmaydi. Davomat imtihon kuni real vaqtda yoziladi (desktop klient,
Telegram Mini App), shuning uchun ma'lumotni imtihon davomida ham, tugagandan
keyin ham olish mumkin.

**API kalitga kerakli ruxsatlar** (admin panel → Rollar):

| Ruxsat | Nima uchun |
|---|---|
| `attendance:read` | Shu bo'limdagi barcha endpointlar |
| `student:all_regions` | Barcha viloyatlar. Bu ruxsat bo'lmasa — faqat API kalit egasiga biriktirilgan viloyat qaytadi (boshqa `region_id` so'ralsa ham), viloyat biriktirilmagan bo'lsa 403 |

**Ish tartibi:**

1. `GET /attendance/sessions` — kerakli test sessiyasini va uning kun+smenalarini toping (`test_session_id`, `session_smena_id`).
2. `GET /attendance/summary` — umumiy sonlar (ixtiyoriy, tekshirish uchun).
3. `GET /attendance/students` — nomzodlar ro'yxatini sahifama-sahifa oling (`after_id` → `next_after_id`).

### 3.1 Test sessiyalari ro'yxati

```
GET /api/v1/attendance/sessions
```

**Query parametrlar** (hammasi ixtiyoriy):

| Parametr | Tur | Tavsif |
|---|---|---|
| `date_from` | date (`YYYY-MM-DD`) | Shu sanada yoki undan keyin tugaydigan sessiyalar |
| `date_to` | date (`YYYY-MM-DD`) | Shu sanada yoki undan oldin boshlanadigan sessiyalar |
| `limit` | integer | 1–100, standart 50 |

Sessiyalar eng yangisidan boshlab tartiblanadi.

**Response (200):**
```json
{
  "items": [
    {
      "test_session_id": 7,
      "name": "Oktabr 2026",
      "test_name": "Milliy sertifikat",
      "start_date": "2026-10-12",
      "finish_date": "2026-10-13",
      "state_key": 4,
      "state_name": "Faol",
      "smenas": [
        { "session_smena_id": 70, "day": "2026-10-12", "smena_name": "1-smena", "number": 1 },
        { "session_smena_id": 71, "day": "2026-10-12", "smena_name": "2-smena", "number": 2 }
      ]
    }
  ],
  "total": 1
}
```

| Field | Tur | Tavsif |
|---|---|---|
| `test_session_id` | integer | Test sessiya ID si — keyingi so'rovlarda kerak |
| `name` | string | Sessiya nomi |
| `test_name` | string \| null | Test turi |
| `start_date`, `finish_date` | date | Sessiya boshlanishi va tugashi |
| `state_key` | integer \| null | Holat: `1` yaratilgan, `2` nomzodlar yuklanmoqda, `3` yuz shablonlari tayyorlanmoqda, `4` faol (imtihon), `5` yakunlangan |
| `state_name` | string \| null | Holat nomi |
| `smenas[].session_smena_id` | integer | Kun+smena ID si |
| `smenas[].day` | date | Imtihon kuni |
| `smenas[].smena_name` | string \| null | Smena nomi |
| `smenas[].number` | integer | Smena tartib raqami |

### 3.2 Nomzodlar holati

```
GET /api/v1/attendance/students
```

**Query parametrlar:**

| Parametr | Tur | Majburiy | Tavsif |
|---|---|---|---|
| `test_session_id` | integer | ha | Test sessiya ID si |
| `session_smena_id` | integer | yo'q | Faqat shu kun+smena |
| `exam_date` | date (`YYYY-MM-DD`) | yo'q | Faqat shu imtihon kuni |
| `region_id` | integer | yo'q | Faqat shu viloyat (qamrov qoidasi yuqorida) |
| `zone_id` | integer | yo'q | Faqat shu bino |
| `status` | string | yo'q | `entered`, `cheating` yoki `not_entered` |
| `jshshir` | string | yo'q | Bitta nomzod — 14 xonali JShShIR |
| `after_id` | integer | yo'q | Sahifalash: oldingi javobdagi `next_after_id`. Birinchi sahifa — `0` (standart) |
| `limit` | integer | yo'q | Sahifadagi qatorlar soni, 1–1000, standart 500 |

**Misol:**
```
GET /api/v1/attendance/students?test_session_id=7&session_smena_id=70&limit=500&after_id=0
X-API-Key: sk-xxxx...
```

**Response (200):**
```json
{
  "items": [
    {
      "student_id": 1520431,
      "jshshir": "31234567890123",
      "last_name": "Aliyev",
      "first_name": "Vali",
      "middle_name": "G'aniyevich",
      "test_session_id": 7,
      "session_smena_id": 70,
      "exam_date": "2026-10-12",
      "smena_name": "1-smena",
      "region_id": 1,
      "region_name": "Toshkent shahri",
      "zone_id": 10,
      "zone_name": "1-bino",
      "gr_n": 3,
      "sp_n": 14,
      "subject_name": "Matematika",
      "status": "entered",
      "is_entered": true,
      "is_cheating": false,
      "is_applied": false,
      "entered_at": "2026-10-12T08:15:42+05:00",
      "last_seen_at": "2026-10-12T08:15:42+05:00"
    }
  ],
  "count": 1,
  "has_more": true,
  "next_after_id": 1520431
}
```

| Field | Tur | Tavsif |
|---|---|---|
| `student_id` | integer | Nomzod yozuvining ID si (sessiya ichida yagona) |
| `jshshir` | string \| null | JShShIR (14 xona) |
| `last_name`, `first_name`, `middle_name` | string | F.I.Sh. |
| `test_session_id` | integer | Test sessiya ID si |
| `session_smena_id` | integer | Kun+smena ID si |
| `exam_date` | date | Imtihon kuni |
| `smena_name` | string \| null | Smena nomi |
| `region_id`, `region_name` | integer, string | Viloyat |
| `zone_id`, `zone_name` | integer, string | Bino |
| `gr_n` | integer | Guruh raqami |
| `sp_n` | integer | O'rin (kompyuter) raqami |
| `subject_name` | string \| null | Fan |
| `status` | string | Davomat holati — pastdagi jadvalga qarang |
| `is_entered` | boolean | Binoga kirgan (chetlatilganlarda ham `true`) |
| `is_cheating` | boolean | Chetlatilgan |
| `is_applied` | boolean | Ariza bergan (to'lovni qaytarib olgan) — imtihonga kirmaydi |
| `entered_at` | datetime \| null | Birinchi Face ID vaqti. Faqat kelganlarda; vaqt zonasi bilan (ISO 8601) |
| `last_seen_at` | datetime \| null | Oxirgi Face ID vaqti |
| `count` | integer | Shu sahifadagi qatorlar soni |
| `has_more` | boolean | Keyingi sahifa bormi |
| `next_after_id` | integer \| null | Keyingi so'rovdagi `after_id`. Oxirgi sahifada `null` |

**`status` qiymatlari:**

| Qiymat | Ma'nosi |
|---|---|
| `entered` | Keldi — Face ID dan o'tib binoga kirgan |
| `cheating` | Keldi, lekin qoidabuzarlik uchun chetlatildi |
| `not_entered` | Kelmadi |

"Kelganlar" jami soni = `entered` + `cheating`.

**Sahifalash.** Ro'yxat `student_id` o'sish tartibida qaytadi. Birinchi so'rovda
`after_id=0`, keyingilarida oldingi javobdagi `next_after_id` yuboriladi va
`has_more=false` bo'lguncha davom etiladi. Bu usul davomat yozilib turgan
paytda ham qatorlarni takrorlamaydi va tushirib qoldirmaydi.

**Muhim:**
- Holat o'zgarishi mumkin. Nomzod keyinroq kelishi mumkin, operator xato
  yozilgan davomatni bekor qilishi mumkin (`entered` → `not_entered`) yoki
  nomzodni chetlatishi mumkin (`entered` → `cheating`). Yakuniy natija uchun
  ma'lumotni smena tugagandan keyin qayta oling.
- Tizimda "oxirgi o'zgarganlar" filtri yo'q. Yangilash uchun kerakli smenani
  to'liq qayta oling.
- Bitta JShShIR bir sessiyada bir necha qatorda bo'lishi mumkin (turli fan yoki
  kun). Har qatorning `student_id` si alohida.

### 3.3 Umumiy sonlar

```
GET /api/v1/attendance/summary
```

Query parametrlar `/attendance/students` dagi bilan bir xil: `test_session_id`
(majburiy), `session_smena_id`, `exam_date`, `region_id`, `zone_id`.

**Response (200):**
```json
{
  "test_session_id": 7,
  "total": 12840,
  "entered": 11902,
  "cheating": 14,
  "not_entered": 924,
  "applied": 37
}
```

| Field | Tavsif |
|---|---|
| `total` | Jami nomzodlar |
| `entered` | Keldi |
| `cheating` | Keldi va chetlatildi |
| `not_entered` | Kelmadi |
| `applied` | Ariza bergan. Ular `not_entered` ichida ham hisoblangan |

`entered + cheating + not_entered = total`.

### 3.4 So'rov chegaralari

| Endpoint | Chegara (bitta API kalit uchun) |
|---|---|
| `/attendance/sessions` | 60 so'rov / daqiqa |
| `/attendance/students` | 300 so'rov / daqiqa |
| `/attendance/summary` | 120 so'rov / daqiqa |

Chegaradan oshsa `429` qaytadi — biroz kutib qayta urining.

---

## Task status qiymatlari (1–2-bo'limlar)

| Status | Tavsif |
|---|---|
| `PENDING` | Task navbatda kutmoqda |
| `STARTED` | Task bajarilmoqda |
| `SUCCESS` | Task muvaffaqiyatli tugadi — `result` fieldida natija |
| `FAILURE` | Task xatolik bilan tugadi — `error` fieldida sabab |

---

## Xatolik kodlari

| HTTP kod | Tavsif |
|---|---|
| 202 | Task qabul qilindi |
| 200 | Status/natija qaytarildi |
| 400 | Noto'g'ri so'rov (yaroqsiz base64, rasm hajmi oshdi) |
| 401 | API kalit yaroqsiz yoki berilmagan |
| 403 | Ruxsat yo'q (yoki API kalit egasiga viloyat biriktirilmagan) |
| 404 | Test sessiya topilmadi |
| 422 | Validatsiya xatosi (majburiy fieldlar to'ldirilmagan, JShShIR 14 xonali emas) |
| 429 | So'rovlar chegarasi oshdi yoki navbat to'la — biroz kutib qayta urining |

---

## Polling namunasi (Python)

```python
import requests
import time

API_URL = "https://your-domain.com/api/v1"
API_KEY = "sk-xxxx..."
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY,
}


def verify_photo(img_b64: str, age: int) -> dict:
    """Rasmni tekshirish va natijani kutish."""
    # 1. Task yuborish
    resp = requests.post(
        f"{API_URL}/photo/verify-photo",
        json={"img_b64": img_b64, "age": age},
        headers=HEADERS,
    )
    resp.raise_for_status()
    task_id = resp.json()["task_id"]

    # 2. Natijani kutish (polling)
    for _ in range(40):
        time.sleep(1.5)
        resp = requests.get(
            f"{API_URL}/photo/verify-photo/status/{task_id}",
            headers=HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()

        if data["status"] == "SUCCESS":
            return data["result"]
        if data["status"] == "FAILURE":
            raise Exception(data["error"])

    raise TimeoutError("Task vaqti tugadi")


def verify_two_faces(ps_img_b64: str, lv_img_b64: str) -> dict:
    """Ikki yuzni solishtirish va natijani kutish."""
    # 1. Task yuborish
    resp = requests.post(
        f"{API_URL}/photo/verify-two-face",
        json={"ps_img": ps_img_b64, "lv_img": lv_img_b64},
        headers=HEADERS,
    )
    resp.raise_for_status()
    task_id = resp.json()["task_id"]

    # 2. Natijani kutish (polling)
    for _ in range(40):
        time.sleep(1.5)
        resp = requests.get(
            f"{API_URL}/photo/verify-two-face/status/{task_id}",
            headers=HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()

        if data["status"] == "SUCCESS":
            return data["result"]
        if data["status"] == "FAILURE":
            raise Exception(data["error"])

    raise TimeoutError("Task vaqti tugadi")
```

---

## Davomatni olish namunasi (Python)

```python
import time

import requests

API_URL = "https://your-domain.com/api/v1"
HEADERS = {"X-API-Key": "sk-xxxx..."}


def fetch_attendance(test_session_id: int, session_smena_id: int | None = None) -> list[dict]:
    """Sessiya (yoki bitta smena) nomzodlarining holatini to'liq olish."""
    params = {"test_session_id": test_session_id, "limit": 1000, "after_id": 0}
    if session_smena_id is not None:
        params["session_smena_id"] = session_smena_id

    items: list[dict] = []
    while True:
        resp = requests.get(f"{API_URL}/attendance/students", params=params, headers=HEADERS, timeout=60)
        if resp.status_code == 429:
            time.sleep(int(resp.headers.get("Retry-After", 5)))
            continue
        resp.raise_for_status()
        data = resp.json()
        items.extend(data["items"])
        if not data["has_more"]:
            return items
        params["after_id"] = data["next_after_id"]


students = fetch_attendance(test_session_id=7, session_smena_id=70)
came = [s for s in students if s["status"] in ("entered", "cheating")]
absent = [s for s in students if s["status"] == "not_entered"]
print(f"Keldi: {len(came)}, kelmadi: {len(absent)}")
```
