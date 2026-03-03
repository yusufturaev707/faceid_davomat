from pydantic import BaseModel, Field


class PhotoVerifyRequest(BaseModel):
    """Rasm tekshiruv so'rovi."""
    age: int = Field(..., ge=1, le=120, description="Foydalanuvchi yoshi")
    img_b64: str = Field(..., description="Rasm base64 formatda")


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
