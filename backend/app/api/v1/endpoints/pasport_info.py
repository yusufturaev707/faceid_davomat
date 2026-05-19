"""Pasport info endpoint — GTSP orqali pasport ma'lumotlari va rasmni olish.

Kirish: ps_ser + ps_num (+ ixtiyoriy imei).
Chiqish: FIO, jinsi, rasm (base64 dataURL).

Bu endpoint mavjud `gtsp_client.fetch_gtsp_data` xizmatidan foydalanadi —
boshqa biror logika o'zgartirilmaydi.
"""

from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.permissions import P
from app.dependencies import PermissionChecker
from app.models.user import User
from app.services.gtsp_client import GtspError, GtspNotConfigured, fetch_gtsp_data

logger = logging.getLogger(__name__)
router = APIRouter()


class PasportInfoRequest(BaseModel):
    ps_ser: str = Field(..., min_length=1, max_length=5, description="Pasport seriyasi, masalan AD")
    ps_num: str = Field(..., min_length=1, max_length=10, description="Pasport raqami")
    imei: str | None = Field(default=None, max_length=14, description="IMEI (ixtiyoriy)")


class PasportInfoResponse(BaseModel):
    last_name: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    sex: int | None = Field(default=None, description="1=erkak, 2=ayol")
    sex_label: str | None = None
    ps_ser: str
    ps_num: str
    imei: str | None = None
    photo: str | None = Field(
        default=None, description="Pasport rasmi, base64 dataURL formatida"
    )
    # Qo'shimcha pasport ma'lumotlari
    birth_place: str | None = None
    birth_date: str | None = None
    birth_country: str | None = None
    livestatus: str | None = None
    nationality: str | None = None
    doc_give_place: str | None = None
    matches_date_begin_document: str | None = None
    matches_date_end_document: str | None = None


def _sex_label(sex: int | None) -> str | None:
    if sex == 1:
        return "Erkak"
    if sex == 2:
        return "Ayol"
    return None


@router.post(
    "",
    response_model=PasportInfoResponse,
    summary="Pasport ma'lumotlari (GTSP)",
)
def get_pasport_info(
    body: PasportInfoRequest,
    _: User = Depends(PermissionChecker(P.PASPORT_INFO_READ.code)),
) -> PasportInfoResponse:
    """Pasport ma'lumotlari va rasmini GTSP API orqali olish.

    `ps_ser` + `ps_num` birlashtirilib GTSP API ga so'rov yuboriladi.
    `imei` ixtiyoriy — bo'sh bo'lsa bo'sh satr sifatida uzatiladi.
    """
    ps_value = f"{body.ps_ser.strip().upper()}{body.ps_num.strip()}"
    imei = (body.imei or "").strip()

    logger.info("Pasport info so'rovi: ps=%s, imei=%s", ps_value, imei or "-")

    try:
        result = fetch_gtsp_data(imei or None, ps_value, timeout=15.0)
    except GtspNotConfigured as e:
        raise HTTPException(status_code=500, detail=str(e))
    except GtspError as e:
        status_code = 502 if e.retryable else 400
        raise HTTPException(status_code=status_code, detail=e.message)

    photo_dataurl: str | None = None
    if result.photo:
        photo_dataurl = (
            "data:image/jpeg;base64," + base64.b64encode(result.photo).decode("ascii")
        )

    return PasportInfoResponse(
        last_name=result.last_name,
        first_name=result.first_name,
        middle_name=result.middle_name,
        sex=result.sex,
        sex_label=_sex_label(result.sex),
        ps_ser=body.ps_ser.strip().upper(),
        ps_num=body.ps_num.strip(),
        imei=imei or None,
        photo=photo_dataurl,
        birth_place=result.birth_place,
        birth_date=result.birth_date,
        birth_country=result.birth_country,
        livestatus=result.livestatus,
        nationality=result.nationality,
        doc_give_place=result.doc_give_place,
        matches_date_begin_document=result.matches_date_begin_document,
        matches_date_end_document=result.matches_date_end_document,
    )
