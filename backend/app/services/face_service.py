"""Yuz aniqlash va tekshirish xizmati.

InsightFace modeli bilan yuz aniqlash, solishtirish, rasm saqlash.
PIL/Pillow ishlatilmaydi — faqat cv2.
"""

import logging
import os
import tempfile
import threading
import uuid

import cv2
import numpy as np
from fastapi import HTTPException, status
from insightface.app import FaceAnalysis

from app.config import settings
from app.schemas.photo import (
    EmbeddingResponse,
    ImageSize,
    PalitraRGB,
    PhotoVerifyResponse,
    TwoFaceVerifyResponse,
)
from app.services.image_decoder import decode_base64_image, decode_image_bytes

logger = logging.getLogger("faceid.face_service")

# InsightFace modelini bir marta yuklash (singleton — har worker process uchun)
_face_app: FaceAnalysis | None = None
_face_app_ready = threading.Event()


def init_face_app() -> None:
    """InsightFace modelini yuklash.

    Celery worker_process_init signalida yoki FastAPI lifespan da chaqiriladi.
    Har process uchun faqat 1 marta ishlaydi.
    """
    global _face_app
    if _face_app is not None:
        return
    logger.info("InsightFace model yuklanmoqda...")

    # ONNX intra-op thread sonini sozlash. insightface 0.7.x `get_model` faqat
    # providers/provider_options ni uzatadi — `sess_options` ni EMAS. Shuning
    # uchun sessiya yaratiladigan `PickableInferenceSession` ni vaqtincha
    # monkeypatch qilib, intra_op_num_threads ni kiritamiz. intra_op=1 → har
    # inference 1 yadro, bu embedding'ni ko'p thread bilan parallel qilishga imkon
    # beradi (aks holda bitta inference barcha yadroni egallab, parallel foydasiz).
    intra = settings.FACE_ONNX_INTRA_THREADS
    _orig_pis_init = None
    if intra and intra > 0:
        import onnxruntime as ort
        from insightface.model_zoo import model_zoo as _mz

        _orig_pis_init = _mz.PickableInferenceSession.__init__

        def _patched_pis_init(self, model_path, **kwargs):
            if not kwargs.get("sess_options"):
                so = ort.SessionOptions()
                so.intra_op_num_threads = intra
                so.inter_op_num_threads = 1
                kwargs["sess_options"] = so
            _orig_pis_init(self, model_path, **kwargs)

        _mz.PickableInferenceSession.__init__ = _patched_pis_init

    try:
        _face_app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"],
        )
        det_sz = settings.FACE_DET_SIZE
        det_thresh = settings.FACE_DET_THRESH
        _face_app.prepare(ctx_id=0, det_thresh=det_thresh, det_size=(det_sz, det_sz))
    finally:
        if _orig_pis_init is not None:
            from insightface.model_zoo import model_zoo as _mz
            _mz.PickableInferenceSession.__init__ = _orig_pis_init

    _face_app_ready.set()
    logger.info(
        "InsightFace model tayyor! (intra_op_threads=%s)",
        intra if intra and intra > 0 else "default",
    )


_FACE_APP_WAIT_TIMEOUT = 300


def get_face_app() -> FaceAnalysis:
    """Tayyor modelni olish. Agar hali yuklanmagan bo'lsa, kutadi.

    Birinchi marta InsightFace modelini CDN dan yuklab olish 1-5 daqiqa
    olishi mumkin (~340 MB). Shuning uchun timeout uzun.

    Returns:
        FaceAnalysis instansiyasi.

    Raises:
        RuntimeError: Model timeout ichida yuklanmasa.
    """
    if _face_app is not None:
        return _face_app
    if not _face_app_ready.wait(timeout=_FACE_APP_WAIT_TIMEOUT):
        raise RuntimeError(
            f"FaceAnalysis model {_FACE_APP_WAIT_TIMEOUT}s ichida yuklanmadi"
        )
    return _face_app


def detect_faces(img_bgr: np.ndarray) -> list:
    """InsightFace yordamida yuzlarni aniqlash.

    Args:
        img_bgr: BGR formatdagi rasm.

    Returns:
        Aniqlangan yuzlar ro'yxati.
    """
    app = get_face_app()
    faces = app.get(img_bgr)
    logger.debug("Yuzlar aniqlandi: %d", len(faces))
    return faces


def check_age(faces: list, expected_age: int) -> bool:
    """Aniqlangan yuz yoshini tekshirish (±tolerance).

    Args:
        faces: InsightFace aniqlagan yuzlar.
        expected_age: Kutilgan yosh.

    Returns:
        Yosh tolerance ichida bo'lsa True.
    """
    if not faces:
        return False
    face = faces[0]
    detected_age = face.age
    return abs(detected_age - expected_age) <= settings.AGE_TOLERANCE


def calculate_back_color(img_bgr: np.ndarray) -> list[int]:
    """Rasmning chetlaridan orqa fon rangini aniqlash.

    4 burchakdan 10x10 piksel oladi va o'rtacha hisoblaydi.

    Args:
        img_bgr: BGR formatdagi rasm.

    Returns:
        [R, G, B] formatda fon rangi.
    """
    h, w = img_bgr.shape[:2]
    margin = 10
    corners = [
        img_bgr[0:margin, 0:margin],
        img_bgr[0:margin, w - margin : w],
        img_bgr[h - margin : h, 0:margin],
        img_bgr[h - margin : h, w - margin : w],
    ]
    all_pixels = np.concatenate([c.reshape(-1, 3) for c in corners])
    mean_bgr = np.mean(all_pixels, axis=0).astype(int)
    # BGR -> RGB
    return [int(mean_bgr[2]), int(mean_bgr[1]), int(mean_bgr[0])]


def calculate_palitra(img_bgr: np.ndarray) -> PalitraRGB:
    """Rasm palitrasining min va max RGB qiymatlarini hisoblash.

    Args:
        img_bgr: BGR formatdagi rasm.

    Returns:
        PalitraRGB obyekti.
    """
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    min_vals = np.min(img_rgb.reshape(-1, 3), axis=0).tolist()
    max_vals = np.max(img_rgb.reshape(-1, 3), axis=0).tolist()
    return PalitraRGB(min_palitra=min_vals, max_palitra=max_vals)


def is_background_valid(back_color: list[int]) -> bool:
    """Orqa fon rangini tekshirish (ochiq rang).

    Args:
        back_color: [R, G, B] formatda fon rangi.

    Returns:
        Fon rangi yetarlicha ochiq bo'lsa True.
    """
    return all(c >= settings.BG_COLOR_THRESHOLD for c in back_color)


def is_palitra_valid(palitra: PalitraRGB) -> bool:
    """Palitra qiymatlari minimal chegaradan yuqori ekanligini tekshirish.

    Args:
        palitra: PalitraRGB obyekti.

    Returns:
        Palitra qiymatlari yetarli bo'lsa True.
    """
    return all(v >= settings.MIN_PALITRA_VALUE for v in palitra.min_palitra)


def _atomic_write_webp(img_bgr: np.ndarray, target_path: str, quality: int) -> None:
    """Rasmni WebP formatda atomik yozish: tempfile -> os.replace().

    Args:
        img_bgr: BGR formatdagi rasm.
        target_path: Yakuniy fayl yo'li.
        quality: WebP sifat darajasi (1-100).

    Raises:
        RuntimeError: cv2.imencode muvaffaqiyatsiz bo'lsa.
        OSError: Diskka yozishda xatolik.
    """
    dir_name = os.path.dirname(target_path)
    success, buf = cv2.imencode(".webp", img_bgr, [cv2.IMWRITE_WEBP_QUALITY, quality])
    if not success:
        raise RuntimeError(f"cv2.imencode muvaffaqiyatsiz: {target_path}")

    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        os.write(fd, buf.tobytes())
        os.fsync(fd)
        os.close(fd)
        fd = -1  # closed marker
        os.replace(tmp_path, target_path)
    except BaseException:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def save_image_webp(img_bgr: np.ndarray, uploads_dir: str | None = None) -> str:
    """Rasmni WebP formatda diskka saqlash + thumbnail yaratish.

    Atomic write ishlatiladi — crash bo'lsa buzilgan fayl qolmaydi.

    Args:
        img_bgr: BGR formatdagi rasm.
        uploads_dir: Saqlash papkasi. None bo'lsa UPLOADS_PHOTO_DIR ishlatiladi.

    Returns:
        Fayl nomi (extension siz, masalan '550e8400e29b1234').
    """
    if uploads_dir is None:
        uploads_dir = settings.UPLOADS_PHOTO_DIR
    os.makedirs(uploads_dir, exist_ok=True)

    filename = uuid.uuid4().hex[:16]

    # Original — WebP
    original_path = os.path.join(uploads_dir, f"{filename}.webp")
    _atomic_write_webp(img_bgr, original_path, settings.WEBP_QUALITY)

    # Thumbnail
    h, w = img_bgr.shape[:2]
    thumb_size = settings.THUMBNAIL_SIZE
    ratio = thumb_size / max(w, h)
    thumb_w = int(w * ratio)
    thumb_h = int(h * ratio)
    thumb_bgr = cv2.resize(img_bgr, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
    thumb_path = os.path.join(uploads_dir, f"{filename}_thumb.webp")
    _atomic_write_webp(thumb_bgr, thumb_path, 70)

    logger.debug("Rasm saqlandi: %s (%dx%d)", filename, w, h)
    return filename


def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """Ikki embedding vektori orasidagi cosine o'xshashlikni hisoblash.

    Args:
        emb1: Birinchi embedding vektori.
        emb2: Ikkinchi embedding vektori.

    Returns:
        O'xshashlik balli (0.0 - 1.0).
    """
    dot = np.dot(emb1, emb2)
    norm = np.linalg.norm(emb1) * np.linalg.norm(emb2)
    if norm == 0:
        return 0.0
    return max(float(dot / norm), 0.0)


def compare_two_faces(
    ps_img_b64: str, lv_img_b64: str
) -> tuple[TwoFaceVerifyResponse, np.ndarray, np.ndarray]:
    """Ikki rasmdagi yuzlarni solishtirish.

    Args:
        ps_img_b64: Pasport rasmi base64 formatda.
        lv_img_b64: Jonli rasm base64 formatda.

    Returns:
        (natija, ps_img_bgr, lv_img_bgr) — response va original rasmlar.
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
    # Square root normalizatsiya (γ = 0.5) — cosine qiymatlar past diapazonda siqilgan
    # bo'lib turadi (masalan, 0.2..0.6). γ=0.5 ni qo'llash score'ni tekislashtirib,
    # oraliqlar orasida farqni yaxshi ko'rsatadi. Decision monoton bo'lgani uchun
    # threshold ham aynan shunday transformatsiya qilinadi — verify natijasi saqlanadi.
    score = 0.0
    threshold = float(settings.SIMILARITY_THRESHOLD) ** 0.5

    if ps_detection and lv_detection:
        ps_embedding = ps_faces[0].embedding
        lv_embedding = lv_faces[0].embedding
        raw_score = cosine_similarity(ps_embedding, lv_embedding)
        score = raw_score**0.5

    verified = score >= threshold and ps_detection and lv_detection

    if verified:
        message = f"Yuzlar mos keldi (ball: {score:.4f})"
    elif not ps_detection or not lv_detection:
        message = "Yuz aniqlanmadi"
    else:
        message = f"Yuzlar mos kelmadi (ball: {score:.4f}, chegara: {threshold:.4f})"

    logger.info(
        "Ikki yuz solishtirish: score=%.4f (γ=0.5 norm), threshold=%.4f, verified=%s",
        score,
        threshold,
        verified,
    )

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
    """Rasmdagi yuzni aniqlash va embedding vektorini qaytarish.

    Args:
        img_b64: Base64 kodlangan rasm.

    Returns:
        EmbeddingResponse — yuz embedding va meta-ma'lumot.
    """
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
    embedding_b64: str | None = None
    embedding_bytes_size = 0

    if not detection:
        errors.append("Rasmda yuz aniqlanmadi")
    else:
        face = faces[0]
        embedding = face.embedding.tolist()
        embedding_size = len(embedding)
        # DB ga yoziladigan format bilan bir xil (float32 little-endian).
        # base64 — JSON orqali binary'ni xavfsiz uzatish standarti.
        import base64 as _b64

        blob = embedding_to_bytes(face.embedding)
        if blob is not None:
            embedding_b64 = _b64.b64encode(blob).decode("ascii")
            embedding_bytes_size = len(blob)

    logger.info("Embedding: detection=%s, embedding_size=%d", detection, embedding_size)

    return EmbeddingResponse(
        detection=detection,
        embedding=embedding,
        embedding_size=embedding_size,
        embedding_b64=embedding_b64,
        embedding_bytes_size=embedding_bytes_size,
        file_size_byte=file_size,
        image_width=w,
        image_height=h,
        error_messages=errors,
    )


# === Embedding binary serialization ==================================
#
# DB da embedding `LargeBinary` (PostgreSQL BYTEA) sifatida saqlanadi —
# `student_ps_data.embedding`. Format: float32 little-endian, InsightFace
# `buffalo_l` modeli uchun 512-dim → 2048 bayt.
#
# Bu pattern `embedding_extractor.py:_process_chunk` da o'rnatilgan (sessiya
# studentlari uchun bulk embedding). Yangi yozish/o'qish joylarida bir xil
# format ishlatilishi uchun shu yerda umumiy helperlar.


def embedding_to_bytes(
    embedding: np.ndarray | list[float] | None,
) -> bytes | None:
    """Embedding vektorini binary blob (float32) ga aylantirish.

    `embedding_extractor._process_chunk` bilan bir xil format:
        `np.asarray(emb, dtype=np.float32).tobytes()`

    Args:
        embedding: numpy array, ro'yxat yoki None.

    Returns:
        Binary blob (DB ga `LargeBinary` sifatida yozish uchun) yoki None.
    """
    if embedding is None:
        return None
    arr = np.asarray(embedding, dtype=np.float32)
    if arr.size == 0:
        return None
    return arr.tobytes()


def bytes_to_embedding(blob: bytes | None) -> np.ndarray | None:
    """Binary blob'dan numpy float32 embedding vektorini qayta tiklash.

    DB dan `LargeBinary` ustun o'qilganda — solishtirish yoki retraining uchun.

    Args:
        blob: Float32 bytes (yoki bo'sh/None).

    Returns:
        1D numpy float32 array yoki None.
    """
    if not blob:
        return None
    return np.frombuffer(blob, dtype=np.float32)


def extract_embedding_blob(image: str | bytes) -> bytes | None:
    """Rasm fayldan (bytes) yoki base64 stringdan yuz embedding olib,
    DB ga yozishga tayyor binary blob qaytarish.

    Yuz aniqlanmasa — None. Foydalanish joylari:
      - Excel/API student loader (ps_img blob bor — bytes yo'li)
      - Davomat bot endpointlari (selfie b64 keladi — base64 yo'li)
      - Test/admin tools

    Args:
        image: Base64 string yoki xom rasm baytlari.

    Returns:
        float32 little-endian bytes (DB `LargeBinary`) yoki yuz topilmasa None.
    """
    if isinstance(image, str):
        img_bgr, _ = decode_base64_image(image)
    else:
        img_bgr, _ = decode_image_bytes(image)

    faces = detect_faces(img_bgr)
    if not faces:
        return None
    return embedding_to_bytes(faces[0].embedding)


def verify_photo(img_b64: str, age: int) -> tuple[PhotoVerifyResponse, np.ndarray]:
    """Rasmni to'liq tekshirish — asosiy biznes logikasi.

    Args:
        img_b64: Base64 kodlangan rasm.
        age: Kutilgan yosh.

    Returns:
        (natija, img_bgr) — natija va original rasm massivi.
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

    logger.info(
        "Rasm tekshiruvi: success=%s, detection=%s, age_match=%s, size=%dx%d",
        success,
        detection,
        age_match,
        w,
        h,
    )

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
