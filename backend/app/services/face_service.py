import base64
import io
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from fastapi import HTTPException, status
from insightface.app import FaceAnalysis
from PIL import Image

from app.config import settings
from app.schemas.photo import (
    EmbeddingResponse,
    ImageSize,
    PalitraRGB,
    PhotoVerifyResponse,
    TwoFaceVerifyResponse,
)

_io_pool = ThreadPoolExecutor(max_workers=4)

# InsightFace modelini bir marta yuklash (singleton)
_face_app: FaceAnalysis | None = None
_face_app_ready = threading.Event()


def init_face_app() -> None:
    """Tizim ishga tushganda modelni yuklash (lifespan da background threadda chaqiriladi)."""
    global _face_app
    if _face_app is not None:
        return
    print("InsightFace model yuklanmoqda...")
    _face_app = FaceAnalysis(
        name="buffalo_l",
        providers=["CPUExecutionProvider"],
    )
    det_sz = settings.FACE_DET_SIZE
    det_thresh = settings.FACE_DET_THRESH
    _face_app.prepare(ctx_id=0, det_thresh=det_thresh, det_size=(det_sz, det_sz))
    _face_app_ready.set()
    print("InsightFace model tayyor!")


def get_face_app() -> FaceAnalysis:
    """Tayyor modelni olish. Agar hali yuklanmagan bo'lsa, kutadi."""
    _face_app_ready.wait()
    return _face_app


def decode_base64_image(img_b64: str) -> tuple[np.ndarray, float]:
    """Base64 rasmni dekodlash va numpy arrayga aylantirish.
    Returns: (image_array, file_size_bytes)
    """
    # Data URL prefiksini olib tashlash (agar mavjud bo'lsa)
    if "," in img_b64:
        img_b64 = img_b64.split(",", 1)[1]

    # Hajm tekshiruvi
    raw_size = len(img_b64)
    if raw_size > settings.MAX_BASE64_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rasm hajmi {settings.MAX_BASE64_SIZE // (1024 * 1024)}MB dan oshmasligi kerak",
        )

    try:
        img_bytes = base64.b64decode(img_b64)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Base64 dekodlash xatosi: yaroqsiz format",
        )

    file_size = len(img_bytes)

    # PIL orqali ochish va numpy arrayga aylantirish
    try:
        pil_image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img_array = np.array(pil_image)
        # OpenCV BGR formatiga aylantirish
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rasmni ochishda xatolik: yaroqsiz rasm formati",
        )

    return img_bgr, float(file_size)


def detect_faces(img_bgr: np.ndarray) -> list:
    """InsightFace yordamida yuzlarni aniqlash."""
    app = get_face_app()
    faces = app.get(img_bgr)
    return faces


def check_age(faces: list, expected_age: int) -> bool:
    """Aniqlangan yuz yoshini tekshirish (±tolerance)."""
    if not faces:
        return False
    # Birinchi (eng katta) yuzni olish
    face = faces[0]
    detected_age = face.age
    return abs(detected_age - expected_age) <= settings.AGE_TOLERANCE


def calculate_back_color(img_bgr: np.ndarray) -> list[int]:
    """Rasmning chetlaridan orqa fon rangini aniqlash.
    4 burchakdan 10x10 piksel oladi va o'rtacha hisoblaydi.
    """
    h, w = img_bgr.shape[:2]
    margin = 10
    corners = [
        img_bgr[0:margin, 0:margin],  # chap-yuqori
        img_bgr[0:margin, w - margin : w],  # o'ng-yuqori
        img_bgr[h - margin : h, 0:margin],  # chap-pastki
        img_bgr[h - margin : h, w - margin : w],  # o'ng-pastki
    ]
    all_pixels = np.concatenate([c.reshape(-1, 3) for c in corners])
    mean_bgr = np.mean(all_pixels, axis=0).astype(int)
    # BGR -> RGB formatga aylantirish
    return [int(mean_bgr[2]), int(mean_bgr[1]), int(mean_bgr[0])]


def calculate_palitra(img_bgr: np.ndarray) -> PalitraRGB:
    """Rasm palitrasining min va max RGB qiymatlarini hisoblash."""
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    min_vals = np.min(img_rgb.reshape(-1, 3), axis=0).tolist()
    max_vals = np.max(img_rgb.reshape(-1, 3), axis=0).tolist()
    return PalitraRGB(min_palitra=min_vals, max_palitra=max_vals)


def is_background_valid(back_color: list[int]) -> bool:
    """Orqa fon rangini tekshirish (ochiq rang: oq, kulrang, och ko'k va h.k.)."""
    return all(c >= settings.BG_COLOR_THRESHOLD for c in back_color)


def is_palitra_valid(palitra: PalitraRGB) -> bool:
    """Palitra qiymatlari minimal chegaradan yuqori ekanligini tekshirish."""
    return all(v >= settings.MIN_PALITRA_VALUE for v in palitra.min_palitra)


def save_image_webp(img_bgr: np.ndarray, uploads_dir: str | None = None) -> str:
    """Rasmni WebP formatda diskka saqlash + thumbnail yaratish.
    Returns: fayl nomi (extension siz, masalan '550e8400-e29b')
    """
    if uploads_dir is None:
        uploads_dir = settings.UPLOADS_PHOTO_DIR
    os.makedirs(uploads_dir, exist_ok=True)

    filename = uuid.uuid4().hex[:16]

    # Original — WebP formatda saqlash
    pil_img = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    original_path = os.path.join(uploads_dir, f"{filename}.webp")
    pil_img.save(original_path, "WEBP", quality=settings.WEBP_QUALITY)

    # Thumbnail — kichik versiya
    thumb_size = settings.THUMBNAIL_SIZE
    ratio = thumb_size / max(pil_img.width, pil_img.height)
    thumb_w = int(pil_img.width * ratio)
    thumb_h = int(pil_img.height * ratio)
    thumb_img = pil_img.resize((thumb_w, thumb_h), Image.LANCZOS)
    thumb_path = os.path.join(uploads_dir, f"{filename}_thumb.webp")
    thumb_img.save(thumb_path, "WEBP", quality=70)

    return filename


def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """Ikki embedding vektori orasidagi cosine o'xshashlikni hisoblash."""
    dot = np.dot(emb1, emb2)
    norm = np.linalg.norm(emb1) * np.linalg.norm(emb2)
    if norm == 0:
        return 0.0
    return max(float(dot / norm), 0.0)


def compare_two_faces(
    ps_img_b64: str, lv_img_b64: str
) -> tuple[TwoFaceVerifyResponse, np.ndarray, np.ndarray]:
    """Ikki rasmdagi yuzlarni solishtirish.
    Returns: (natija, ps_img_bgr, lv_img_bgr)
    """
    errors: list[str] = []

    # 1. Rasmlarni dekodlash
    ps_img_bgr, ps_file_size = decode_base64_image(ps_img_b64)
    lv_img_bgr, lv_file_size = decode_base64_image(lv_img_b64)

    # 2. O'lchamlarni olish
    ps_h, ps_w = ps_img_bgr.shape[:2]
    lv_h, lv_w = lv_img_bgr.shape[:2]

    # 3. Yuzlarni aniqlash
    ps_faces = detect_faces(ps_img_bgr)
    lv_faces = detect_faces(lv_img_bgr)
    ps_detection = len(ps_faces) > 0
    lv_detection = len(lv_faces) > 0

    if not ps_detection:
        errors.append("Pasport rasmida yuz aniqlanmadi")
    if not lv_detection:
        errors.append("Jonli rasmda yuz aniqlanmadi")

    # 4. Cosine similarity hisoblash
    score = 0.0
    threshold = settings.SIMILARITY_THRESHOLD

    if ps_detection and lv_detection:
        ps_embedding = ps_faces[0].embedding
        lv_embedding = lv_faces[0].embedding
        score = cosine_similarity(ps_embedding, lv_embedding)

    verified = score >= threshold and ps_detection and lv_detection

    if verified:
        message = f"Yuzlar mos keldi (ball: {score:.4f})"
    elif not ps_detection or not lv_detection:
        message = "Yuz aniqlanmadi"
    else:
        message = f"Yuzlar mos kelmadi (ball: {score:.4f}, chegara: {threshold})"

    response = TwoFaceVerifyResponse(
        score=round(score, 4),
        thresh_score=threshold,
        verified=verified,
        message=message,
        ps_detection=ps_detection,
        lv_detection=lv_detection,
        ps_file_size=int(ps_file_size),
        lv_file_size=int(lv_file_size),
        ps_width=ps_w,
        ps_height=ps_h,
        lv_width=lv_w,
        lv_height=lv_h,
        error_messages=errors,
    )
    return response, ps_img_bgr, lv_img_bgr


def extract_embedding(img_b64: str) -> EmbeddingResponse:
    """Rasmdagi yuzni aniqlash va embedding vektorini qaytarish."""
    # 1. Base64 dekodlash
    img_bgr, file_size = decode_base64_image(img_b64)

    # 2. O'lchamlarni olish
    h, w = img_bgr.shape[:2]

    # 3. Yuzni aniqlash
    faces = detect_faces(img_bgr)
    detection = len(faces) > 0

    errors: list[str] = []
    embedding: list[float] = []
    embedding_size = 0

    if not detection:
        errors.append("Rasmda yuz aniqlanmadi")
    else:
        face = faces[0]
        embedding = face.embedding.tolist()
        embedding_size = len(embedding)

    return EmbeddingResponse(
        detection=detection,
        embedding=embedding,
        embedding_size=embedding_size,
        file_size_byte=file_size,
        image_width=w,
        image_height=h,
        error_messages=errors,
    )


def verify_photo(img_b64: str, age: int) -> tuple[PhotoVerifyResponse, np.ndarray]:
    """Rasmni to'liq tekshirish — asosiy biznes logikasi.
    Returns: (natija, img_bgr) — natija va original rasm massivi
    """
    # 1. Base64 dekodlash
    img_bgr, file_size = decode_base64_image(img_b64)

    # 2. O'lchamlarni olish
    h, w = img_bgr.shape[:2]
    size = ImageSize(height=h, width=w)

    # 3. Yuzni aniqlash
    faces = detect_faces(img_bgr)
    detection = len(faces) > 0

    # 4. Yosh tekshiruvi
    age_match = check_age(faces, age) if detection else False

    # 5. Orqa fon rangi
    back_color = calculate_back_color(img_bgr)

    # 6. Palitra
    palitra = calculate_palitra(img_bgr)

    # 7. Xatoliklarni yig'ish
    errors: list[str] = []
    if not detection:
        errors.append("Rasmda yuz aniqlanmadi")
    if detection and not age_match:
        detected_age = faces[0].age if faces else 0
        errors.append(
            f"Yosh mos kelmadi: kiritilgan {age}, aniqlangan ~{detected_age} (±{settings.AGE_TOLERANCE})"
        )
    if not (
        settings.MIN_WIDTH <= w <= settings.MAX_WIDTH
        and settings.MIN_HEIGHT <= h <= settings.MAX_HEIGHT
    ):
        errors.append(
            f"O'lcham noto'g'ri: {w}x{h}, talab: {settings.MIN_WIDTH}-{settings.MAX_WIDTH} x {settings.MIN_HEIGHT}-{settings.MAX_HEIGHT}"
        )
    if not is_background_valid(back_color):
        errors.append(
            f"Orqa fon juda qorong'i: RGB({back_color[0]}, {back_color[1]}, {back_color[2]})"
        )
    if not is_palitra_valid(palitra):
        errors.append(
            f"Palitra minimal: RGB({palitra.min_palitra[0]}, {palitra.min_palitra[1]}, {palitra.min_palitra[2]}), talab: ≥{settings.MIN_PALITRA_VALUE}"
        )

    success = len(errors) == 0

    response = PhotoVerifyResponse(
        success=success,
        back_color=back_color,
        size=size,
        palitra_rgb=palitra,
        detection=detection,
        file_size_byte=file_size,
        error_messages=errors,
    )
    return response, img_bgr
