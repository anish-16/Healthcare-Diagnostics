from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.models import CentreTest, DiagnosticCentre
from app.schemas.catalog import CentreOut, CentreTestOut, CentreWithTestsOut

router = APIRouter(prefix="/api/centres", tags=["Diagnostic Centres"])


@router.get("", response_model=list[CentreOut], summary="List diagnostic centres")
def list_centres(db: Annotated[Session, Depends(get_db)]):
    return db.query(DiagnosticCentre).order_by(DiagnosticCentre.name).all()


@router.get("/{centre_id}", response_model=CentreOut, summary="Get a diagnostic centre by id")
def get_centre(centre_id: int, db: Annotated[Session, Depends(get_db)]):
    centre = db.get(DiagnosticCentre, centre_id)
    if centre is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centre not found")
    return centre


@router.get("/{centre_id}/tests", response_model=CentreWithTestsOut,
            summary="List the tests available at a centre, with per-centre prices")
def list_centre_tests(centre_id: int, db: Annotated[Session, Depends(get_db)]):
    centre = db.get(DiagnosticCentre, centre_id)
    if centre is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centre not found")
    offerings = (
        db.query(CentreTest)
        .options(joinedload(CentreTest.test))
        .filter(CentreTest.centre_id == centre_id)
        .all()
    )
    return CentreWithTestsOut(
        id=centre.id,
        name=centre.name,
        location=centre.location,
        created_at=centre.created_at,
        updated_at=centre.updated_at,
        tests=[CentreTestOut.model_validate(o) for o in offerings],
    )
