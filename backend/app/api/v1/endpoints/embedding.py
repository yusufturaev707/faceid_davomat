import asyncio

from fastapi import APIRouter, Depends

from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.photo import EmbeddingRequest, EmbeddingResponse
from app.services.face_service import extract_embedding

router = APIRouter()


@router.post(
    "/extract",
    response_model=EmbeddingResponse,
    summary="Yuz embedding vektorini olish",
    description="Rasmdagi yuzni aniqlaydi va embedding vektorini qaytaradi. Celery ishlatilmaydi.",
)
async def get_embedding(
    request: EmbeddingRequest,
    _current_user: User = Depends(get_current_active_user),
) -> EmbeddingResponse:
    """Rasmdan yuz embeddingni olish (asinxron)."""
    result = await asyncio.to_thread(extract_embedding, request.img_b64)
    return result
