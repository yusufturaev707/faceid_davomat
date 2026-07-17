"""Natija uchun tahlil endpoint.

Tashqi natija tizimidan (Excel/Access) joylangan qatorlarni FaceID bazasidagi
talabalar bilan `imei` bo'yicha solishtirib, nomuvofiqliklarni topadi
(masalan chetlatilgan bo'lsa-yu natija chiqqan). Faqat `result_analysis:read`
huquqiga ega foydalanuvchilar uchun.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions import P
from app.crud import result_analysis as crud
from app.dependencies import PermissionChecker, get_db
from app.models.user import User
from app.schemas.result_analysis import (
    ResultAnalysisRequest,
    ResultAnalysisResponse,
    ScopeSession,
)

router = APIRouter()

_ANALYZE = PermissionChecker(P.RESULT_ANALYSIS_READ.code)


@router.get("/sessions", response_model=list[ScopeSession])
def scope_sessions(
    test_id: int = Query(..., description="Test id"),
    db: Session = Depends(get_db),
    _: User = Depends(_ANALYZE),
) -> list[ScopeSession]:
    """Test bo'yicha aktiv sessiyalar va ularning test kunlari (forma uchun)."""
    return crud.get_scope_sessions(db, test_id=test_id)


@router.post("/analyze", response_model=ResultAnalysisResponse)
def analyze(
    body: ResultAnalysisRequest,
    db: Session = Depends(get_db),
    _: User = Depends(_ANALYZE),
) -> ResultAnalysisResponse:
    return crud.analyze_results(
        db,
        test_session_id=body.test_session_id,
        day=body.day,
        mode=body.mode,
        rows=body.rows,
    )
