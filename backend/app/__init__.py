"""FaceID backend paketi.

Bu fayl har jarayonda (uvicorn/gunicorn, Celery worker, skriptlar) `app.*`
modullaridan OLDIN bajariladi — shuning uchun jarayon darajasidagi xavfsizlik
sozlamalari shu yerda.
"""

import os

# Dekompressiya bomba himoyasi: OpenCV piksel chegarasini rasm ochishdan OLDIN
# (sarlavhadan o'lcham o'qilgach, xotira ajratilmasdan) tekshiradi. Standart
# qiymat ~1 milliard piksel — ~1 MB base64 PNG 30000×30000 bo'lib ~2.7 GB BGR
# xotira olardi. Qiymat `cv2` import qilinganda bir marta o'qiladi, keyin
# o'zgartirish ta'sir qilmaydi — shuning uchun hech qaysi modul `cv2` ni bundan
# oldin import qilmasligi kerak. `image_decoder.MAX_IMAGE_PIXELS` bilan bir xil.
os.environ.setdefault("OPENCV_IO_MAX_IMAGE_PIXELS", str(64 * 1024 * 1024))
