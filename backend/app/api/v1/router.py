from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, embedding, photo

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(photo.router, prefix="/photo", tags=["photo"])
api_router.include_router(embedding.router, prefix="/embedding", tags=["embedding"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
