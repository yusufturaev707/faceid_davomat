from pydantic import BaseModel, Field


class PhotoVerifyRequest(BaseModel):
    """Rasm tekshiruv so'rovi."""
    age: int = Field(..., ge=1, le=120, description="Foydalanuvchi yoshi", examples=[25])
    img_b64: str = Field(..., description="Rasm base64 formatda (data:image/jpeg;base64,... yoki sof base64)", examples=["<base64_string_here>"])


class ImageSize(BaseModel):
    """Rasm o'lchamlari."""
    height: int
    width: int


class PalitraRGB(BaseModel):
    """RGB palitra min/max qiymatlari."""
    min_palitra: list[int]
    max_palitra: list[int]


class PhotoVerifyResponse(BaseModel):
    """Rasm tekshiruv natijasi."""
    success: bool = Field(..., description="Sertifikat uchun yaroqlilik")
    back_color: list[int] = Field(..., description="Orqa fon rangi [R, G, B]")
    size: ImageSize = Field(..., description="Rasm o'lchamlari")
    palitra_rgb: PalitraRGB = Field(..., description="Palitra RGB qiymatlari")
    detection: bool = Field(..., description="Yuz aniqlangan yoki yo'q")
    file_size_byte: float = Field(..., description="Fayl hajmi baytlarda")
    error_messages: list[str] = Field(default_factory=list, description="Rad etilish sabablari")


class ErrorResponse(BaseModel):
    """Xatolik javobi."""
    detail: str


class TaskSubmitResponse(BaseModel):
    """Celery task yuborilganda qaytariladigan javob."""
    task_id: str


class TaskStatusResponse(BaseModel):
    """Celery task holati va natijasi."""
    task_id: str
    status: str  # PENDING | STARTED | SUCCESS | FAILURE
    result: PhotoVerifyResponse | None = None
    error: str | None = None


# === Ikki yuzni solishtirish ===

class TwoFaceVerifyRequest(BaseModel):
    """Ikki yuzni solishtirish so'rovi."""
    ps_img: str = Field(..., description="Pasport rasmi base64 formatda", examples=["<base64_string_here>"])
    lv_img: str = Field(..., description="Jonli rasm base64 formatda", examples=["<base64_string_here>"])


class TwoFaceVerifyResponse(BaseModel):
    """Ikki yuzni solishtirish natijasi."""
    score: float = Field(..., description="O'xshashlik balli (0.0 - 1.0)")
    thresh_score: float = Field(..., description="Chegara qiymati")
    verified: bool = Field(..., description="Tasdiqlangan yoki yo'q")
    message: str = Field(..., description="Natija xabari")
    ps_detection: bool = Field(..., description="Pasport rasmida yuz aniqlandi")
    lv_detection: bool = Field(..., description="Jonli rasmda yuz aniqlandi")
    ps_file_size: int = Field(..., description="Pasport rasm hajmi (bayt)")
    lv_file_size: int = Field(..., description="Jonli rasm hajmi (bayt)")
    ps_width: int = Field(..., description="Pasport rasm kengligi")
    ps_height: int = Field(..., description="Pasport rasm balandligi")
    lv_width: int = Field(..., description="Jonli rasm kengligi")
    lv_height: int = Field(..., description="Jonli rasm balandligi")
    error_messages: list[str] = Field(default_factory=list, description="Xatolik xabarlari")


class TwoFaceTaskStatusResponse(BaseModel):
    """Ikki yuz solishtirish task holati."""
    task_id: str
    status: str
    result: TwoFaceVerifyResponse | None = None
    error: str | None = None
