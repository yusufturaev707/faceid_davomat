"""Natija uchun tahlil endpoint.

Tashqi natija tizimidan (Excel/Access) joylangan qatorlarni FaceID bazasidagi
talabalar bilan `imei` bo'yicha solishtirib, nomuvofiqliklarni topadi
(masalan chetlatilgan bo'lsa-yu natija chiqqan). Faqat `result_analysis:read`
huquqiga ega foydalanuvchilar uchun.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.permissions import P
from app.crud import result_analysis as crud
from app.dependencies import PermissionChecker, get_db
from app.models.user import User
from app.schemas.result_analysis import (
    ResultAnalysisRequest,
    ResultAnalysisResponse,
)

router = APIRouter()

_ANALYZE = PermissionChecker(P.RESULT_ANALYSIS_READ.code)


@router.post("/analyze", response_model=ResultAnalysisResponse)
def analyze(
    body: ResultAnalysisRequest,
    db: Session = Depends(get_db),
    _: User = Depends(_ANALYZE),
) -> ResultAnalysisResponse:
    if body.date_from > body.date_to:
        raise HTTPException(
            status_code=400,
            detail="Boshlanish sanasi tugash sanasidan katta bo'lmasin",
        )
    return crud.analyze_results(
        db,
        test_id=body.test_id,
        smena_id=body.smena_id,
        date_from=body.date_from,
        date_to=body.date_to,
        mode=body.mode,
        rows=body.rows,
    )
