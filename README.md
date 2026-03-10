# faceid_api
Face Id
Tashqi tizim uchun faqat dokumentatsiya:

 # 1. Rasm yuborish
 POST /api/v1/photo/verify-photo
 X-API-Key: sk-xxxx...
 Body: {"img_b64": "...", "age": 25}
 Response: {"task_id": "abc-123"}

 # 2. Natijani olish (1-2 soniya oraliqda polling)
 GET /api/v1/photo/verify-photo/status/abc-123
 X-API-Key: sk-xxxx...
 Response: {"status": "SUCCESS", "result": {...}}
