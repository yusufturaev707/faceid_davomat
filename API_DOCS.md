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

Nomzodni test turi va tashqi platformadagi ID si bo'yicha topib, imtihonga
kelgan-kelmaganini qaytaradi. Faqat o'qish — tizimda hech narsa
o'zgartirilmaydi. Davomat imtihon kuni real vaqtda yoziladi (desktop klient,
Telegram Mini App), shuning uchun holatni imtihon davomida ham, tugagandan
keyin ham so'rash mumkin.

**API kalitga kerakli ruxsatlar** (admin panel → Rollar):

| Ruxsat | Nima uchun |
|---|---|
| `attendance:read` | Shu bo'limdagi endpoint |
| `student:all_regions` | Barcha viloyatlar nomzodlari. Bu ruxsat bo'lmasa — faqat API kalit egasiga biriktirilgan viloyat nomzodlari topiladi (boshqasi uchun 404), viloyat biriktirilmagan bo'lsa 403 |

### 3.1 Nomzodni topish

```
GET /api/v1/attendance/student?test_key={test_key}&task_id={task_id}
```

**Query parametrlar** (ikkalasi ham majburiy):

| Parametr | Tur | Tavsif |
|---|---|---|
| `test_key` | string (1–20 belgi) | Test turi kaliti, masalan `ms`, `cefr`. Katta-kichik harf farqlanadi |
| `task_id` | integer (≥ 1) | Nomzodning sizning platformangizdagi unikal ID si — nomzodlar ro'yxati FaceID tizimiga yuklanganda shu qiymat saqlangan |

Parametrlardan biri berilmasa, `task_id` son bo'lmasa yoki `0` bo'lsa — `422`.

> Bu `task_id` — nomzodning **sizning platformangizdagi** ID si (son). 1–2-bo'limlardagi
> `task_id` (rasm tekshirish vazifasining UUID si) bilan aloqasi yo'q.

**Misol:**
```
GET /api/v1/attendance/student?test_key=ms&task_id=845120
X-API-Key: sk-xxxx...
```

**Response (200):**
```json
{
  "test_key": "ms",
  "task_id": 845120,
  "count": 1,
  "items": [
    {
      "student_id": 1520431,
      "task_id": 845120,
      "jshshir": "31234567890123",
      "last_name": "ALIYEV",
      "first_name": "VALI",
      "middle_name": "G'ANIYEVICH",
      "test_key": "ms",
      "test_name": "Milliy sertifikat",
      "test_session_id": 7,
      "test_session_name": "Oktabr 2026",
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
  ]
}
```

**Topilmasa (404):**
```json
{ "detail": "Nomzod topilmadi" }
```

`404` quyidagi hollarda qaytadi: bunday `test_key` + `task_id` juftligi yo'q,
nomzod hali tizimga yuklanmagan yoki u API kalit qamrovidan tashqaridagi
viloyatda.

| Field | Tur | Tavsif |
|---|---|---|
| `test_key`, `task_id` | string, integer | So'rovdagi qiymatlar |
| `count` | integer | `items` dagi qatorlar soni |
| `items[].student_id` | integer | Nomzod yozuvining FaceID tizimidagi ID si |
| `items[].task_id` | integer | Tashqi platformadagi ID |
| `items[].jshshir` | string \| null | JShShIR (14 xona) |
| `items[].last_name`, `first_name`, `middle_name` | string | F.I.Sh. |
| `items[].test_key`, `test_name` | string | Test turi |
| `items[].test_session_id`, `test_session_name` | integer, string | Test sessiyasi |
| `items[].session_smena_id` | integer | Kun+smena ID si |
| `items[].exam_date` | date | Imtihon kuni |
| `items[].smena_name` | string \| null | Smena nomi |
| `items[].region_id`, `region_name` | integer, string | Viloyat |
| `items[].zone_id`, `zone_name` | integer, string | Bino |
| `items[].gr_n` | integer | Guruh raqami |
| `items[].sp_n` | integer | O'rin (kompyuter) raqami |
| `items[].subject_name` | string \| null | Fan |
| `items[].status` | string | Davomat holati — pastdagi jadvalga qarang |
| `items[].is_entered` | boolean | Binoga kirgan (chetlatilganlarda ham `true`) |
| `items[].is_cheating` | boolean | Chetlatilgan |
| `items[].is_applied` | boolean | Ariza bergan (to'lovni qaytarib olgan) — imtihonga kirmaydi |
| `items[].entered_at` | datetime \| null | Birinchi Face ID vaqti. Faqat kelganlarda; vaqt zonasi bilan (ISO 8601) |
| `items[].last_seen_at` | datetime \| null | Oxirgi Face ID vaqti |

**`status` qiymatlari:**

| Qiymat | Ma'nosi |
|---|---|
| `entered` | Keldi — Face ID dan o'tib binoga kirgan |
| `cheating` | Keldi, lekin qoidabuzarlik uchun chetlatildi |
| `not_entered` | Kelmadi |

Nomzod kelgan hisoblanadi, agar `status` — `entered` yoki `cheating` bo'lsa.

**Nega `items` ro'yxat.** Odatda bitta qator qaytadi. Bir nechta qator
bo'lishi mumkin, agar shu test turida nomzod bir nechta sessiyaga (masalan,
qayta topshirish) yoki bir sessiyada bir nechta qatorga yuklangan bo'lsa.
Qatorlar eng yangi imtihon sanasidan boshlab tartiblanadi — joriy imtihon
uchun odatda `items[0]` kerak; aniq imtihonni `test_session_id` /
`exam_date` bo'yicha tanlang. Bitta javobda ko'pi bilan 50 qator.

**Muhim:** holat o'zgarishi mumkin. Nomzod keyinroq kelishi mumkin, operator
xato yozilgan davomatni bekor qilishi mumkin (`entered` → `not_entered`) yoki
nomzodni chetlatishi mumkin (`entered` → `cheating`). Yakuniy natija uchun
smena tugagandan keyin qayta so'rang.

### 3.2 So'rov chegarasi

Bitta API kalit uchun **600 so'rov / daqiqa**. Chegaradan oshsa `429`
qaytadi — bir necha soniya kutib qayta urining.

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
| 404 | Nomzod topilmadi (3-bo'lim) |
| 422 | Validatsiya xatosi (majburiy fieldlar to'ldirilmagan, `task_id` son emas yoki 0) |
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


def get_attendance(test_key: str, task_id: int) -> dict | None:
    """Nomzodning eng yangi imtihondagi davomati. Topilmasa — None."""
    params = {"test_key": test_key, "task_id": task_id}
    while True:
        resp = requests.get(f"{API_URL}/attendance/student", params=params, headers=HEADERS, timeout=15)
        if resp.statutask_id == 429:
            time.sleep(5)
            continue
        if resp.statutask_id == 404:
            return None
        resp.raise_for_status()
        return resp.json()["items"][0]


row = get_attendance("ms", 845120)
if row is None:
    print("Nomzod topilmadi")
else:
    came = row["status"] in ("entered", "cheating")
    print(f"{row['last_name']} {row['first_name']}: {'keldi' if came else 'kelmadi'}")
```
