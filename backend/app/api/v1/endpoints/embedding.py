import asyncio

from fastapi import APIRouter, Depends, Request

from app.core.permissions import P
from app.core.rate_limit import limiter
from app.dependencies import PermissionChecker
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
@limiter.limit("1000/minute")
async def get_embedding(
    request: Request,
    payload: EmbeddingRequest,
    _current_user: User = Depends(PermissionChecker(P.EMBEDDING_EXTRACT.code)),
) -> EmbeddingResponse:
    """Rasmdan yuz embeddingni olish (asinxron)."""
    result = await asyncio.to_thread(extract_embedding, payload.img_b64)
    return result
