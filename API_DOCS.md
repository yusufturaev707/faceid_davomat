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

## Status qiymatlari

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
| 403 | Ruxsat yo'q |
| 422 | Validatsiya xatosi (majburiy fieldlar to'ldirilmagan) |

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
