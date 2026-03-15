"""CRUD endpoints for all lookup/reference tables."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import lookup as crud
from app.crud.lookup import DuplicateError
from app.dependencies import get_current_active_user, get_db, require_admin
from app.models.user import User
from app.schemas import lookup as schemas

router = APIRouter()


def _handle_duplicate(e: DuplicateError):
    """Convert DuplicateError to 409 Conflict HTTPException."""
    raise HTTPException(status_code=409, detail=e.message)


# ===================== TEST =====================

@router.get("/tests", response_model=list[schemas.TestResponse], tags=["tests"])
def list_tests(db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    return crud.get_tests(db)


@router.post("/tests", response_model=schemas.TestResponse, status_code=201, tags=["tests"])
def create_test(body: schemas.TestCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        return crud.create_test(db, body.model_dump())
    except DuplicateError as e:
        _handle_duplicate(e)


@router.patch("/tests/{item_id}", response_model=schemas.TestResponse, tags=["tests"])
def update_test(item_id: int, body: schemas.TestUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        obj = crud.update_test(db, item_id, body.model_dump(exclude_unset=True))
    except DuplicateError as e:
        _handle_duplicate(e)
    if not obj:
        raise HTTPException(404, "Topilmadi")
    return obj


@router.delete("/tests/{item_id}", status_code=204, tags=["tests"])
def delete_test(item_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        if not crud.delete_test(db, item_id):
            raise HTTPException(404, "Topilmadi")
    except DuplicateError as e:
        _handle_duplicate(e)


# ===================== SMENA =====================

@router.get("/smenas", response_model=list[schemas.SmenaResponse], tags=["smenas"])
def list_smenas(db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    return crud.get_smenas(db)


@router.post("/smenas", response_model=schemas.SmenaResponse, status_code=201, tags=["smenas"])
def create_smena(body: schemas.SmenaCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        return crud.create_smena(db, body.model_dump())
    except DuplicateError as e:
        _handle_duplicate(e)


@router.patch("/smenas/{item_id}", response_model=schemas.SmenaResponse, tags=["smenas"])
def update_smena(item_id: int, body: schemas.SmenaUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        obj = crud.update_smena(db, item_id, body.model_dump(exclude_unset=True))
    except DuplicateError as e:
        _handle_duplicate(e)
    if not obj:
        raise HTTPException(404, "Topilmadi")
    return obj


@router.delete("/smenas/{item_id}", status_code=204, tags=["smenas"])
def delete_smena(item_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        if not crud.delete_smena(db, item_id):
            raise HTTPException(404, "Topilmadi")
    except DuplicateError as e:
        _handle_duplicate(e)


# ===================== SESSION STATE =====================

@router.get("/session-states", response_model=list[schemas.SessionStateResponse], tags=["session-states"])
def list_session_states(db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    return crud.get_session_states(db)


@router.post("/session-states", response_model=schemas.SessionStateResponse, status_code=201, tags=["session-states"])
def create_session_state(body: schemas.SessionStateCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        return crud.create_session_state(db, body.model_dump())
    except DuplicateError as e:
        _handle_duplicate(e)


@router.patch("/session-states/{item_id}", response_model=schemas.SessionStateResponse, tags=["session-states"])
def update_session_state(item_id: int, body: schemas.SessionStateUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        obj = crud.update_session_state(db, item_id, body.model_dump(exclude_unset=True))
    except DuplicateError as e:
        _handle_duplicate(e)
    if not obj:
        raise HTTPException(404, "Topilmadi")
    return obj


@router.delete("/session-states/{item_id}", status_code=204, tags=["session-states"])
def delete_session_state(item_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        if not crud.delete_session_state(db, item_id):
            raise HTTPException(404, "Topilmadi")
    except DuplicateError as e:
        _handle_duplicate(e)


# ===================== REGION =====================

@router.get("/regions", response_model=list[schemas.RegionResponse], tags=["regions"])
def list_regions(db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    return crud.get_regions(db)


@router.post("/regions", response_model=schemas.RegionResponse, status_code=201, tags=["regions"])
def create_region(body: schemas.RegionCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        return crud.create_region(db, body.model_dump())
    except DuplicateError as e:
        _handle_duplicate(e)


@router.patch("/regions/{item_id}", response_model=schemas.RegionResponse, tags=["regions"])
def update_region(item_id: int, body: schemas.RegionUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        obj = crud.update_region(db, item_id, body.model_dump(exclude_unset=True))
    except DuplicateError as e:
        _handle_duplicate(e)
    if not obj:
        raise HTTPException(404, "Topilmadi")
    return obj


@router.delete("/regions/{item_id}", status_code=204, tags=["regions"])
def delete_region(item_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        if not crud.delete_region(db, item_id):
            raise HTTPException(404, "Topilmadi")
    except DuplicateError as e:
        _handle_duplicate(e)


# ===================== ZONE =====================

@router.get("/zones", response_model=list[schemas.ZoneResponse], tags=["zones"])
def list_zones(db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    return crud.get_zones(db)


@router.post("/zones", response_model=schemas.ZoneResponse, status_code=201, tags=["zones"])
def create_zone(body: schemas.ZoneCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        return crud.create_zone(db, body.model_dump())
    except DuplicateError as e:
        _handle_duplicate(e)


@router.patch("/zones/{item_id}", response_model=schemas.ZoneResponse, tags=["zones"])
def update_zone(item_id: int, body: schemas.ZoneUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        obj = crud.update_zone(db, item_id, body.model_dump(exclude_unset=True))
    except DuplicateError as e:
        _handle_duplicate(e)
    if not obj:
        raise HTTPException(404, "Topilmadi")
    return obj


@router.delete("/zones/{item_id}", status_code=204, tags=["zones"])
def delete_zone(item_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        if not crud.delete_zone(db, item_id):
            raise HTTPException(404, "Topilmadi")
    except DuplicateError as e:
        _handle_duplicate(e)


# ===================== ROLE =====================

@router.get("/roles", response_model=list[schemas.RoleResponse], tags=["roles"])
def list_roles(db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    return crud.get_roles(db)


@router.post("/roles", response_model=schemas.RoleResponse, status_code=201, tags=["roles"])
def create_role(body: schemas.RoleCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        return crud.create_role(db, body.model_dump())
    except DuplicateError as e:
        _handle_duplicate(e)


@router.patch("/roles/{item_id}", response_model=schemas.RoleResponse, tags=["roles"])
def update_role(item_id: int, body: schemas.RoleUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        obj = crud.update_role(db, item_id, body.model_dump(exclude_unset=True))
    except DuplicateError as e:
        _handle_duplicate(e)
    if not obj:
        raise HTTPException(404, "Topilmadi")
    return obj


@router.delete("/roles/{item_id}", status_code=204, tags=["roles"])
def delete_role(item_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        if not crud.delete_role(db, item_id):
            raise HTTPException(404, "Topilmadi")
    except DuplicateError as e:
        _handle_duplicate(e)


# ===================== REASON =====================

@router.get("/reasons", response_model=list[schemas.ReasonResponse], tags=["reasons"])
def list_reasons(db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    return crud.get_reasons(db)


@router.post("/reasons", response_model=schemas.ReasonResponse, status_code=201, tags=["reasons"])
def create_reason(body: schemas.ReasonCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        return crud.create_reason(db, body.model_dump())
    except DuplicateError as e:
        _handle_duplicate(e)


@router.patch("/reasons/{item_id}", response_model=schemas.ReasonResponse, tags=["reasons"])
def update_reason(item_id: int, body: schemas.ReasonUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        obj = crud.update_reason(db, item_id, body.model_dump(exclude_unset=True))
    except DuplicateError as e:
        _handle_duplicate(e)
    if not obj:
        raise HTTPException(404, "Topilmadi")
    return obj


@router.delete("/reasons/{item_id}", status_code=204, tags=["reasons"])
def delete_reason(item_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        if not crud.delete_reason(db, item_id):
            raise HTTPException(404, "Topilmadi")
    except DuplicateError as e:
        _handle_duplicate(e)


# ===================== STUDENT BLACKLIST =====================

@router.get("/blacklist", response_model=list[schemas.StudentBlacklistResponse], tags=["blacklist"])
def list_blacklist(db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    return crud.get_blacklist(db)


@router.post("/blacklist", response_model=schemas.StudentBlacklistResponse, status_code=201, tags=["blacklist"])
def create_blacklist(body: schemas.StudentBlacklistCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        return crud.create_blacklist_item(db, body.model_dump())
    except DuplicateError as e:
        _handle_duplicate(e)


@router.patch("/blacklist/{item_id}", response_model=schemas.StudentBlacklistResponse, tags=["blacklist"])
def update_blacklist(item_id: int, body: schemas.StudentBlacklistUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        obj = crud.update_blacklist_item(db, item_id, body.model_dump(exclude_unset=True))
    except DuplicateError as e:
        _handle_duplicate(e)
    if not obj:
        raise HTTPException(404, "Topilmadi")
    return obj


@router.delete("/blacklist/{item_id}", status_code=204, tags=["blacklist"])
def delete_blacklist(item_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        if not crud.delete_blacklist_item(db, item_id):
            raise HTTPException(404, "Topilmadi")
    except DuplicateError as e:
        _handle_duplicate(e)
