from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import CentreTest, DiagnosticTest
from app.schemas.catalog import CentreTestOut, TestOut

router = APIRouter(prefix="/api/tests", tags=["Diagnostic Tests"])


@router.get("", response_model=list[TestOut], summary="List diagnostic tests")
def list_tests(db: Annotated[Session, Depends(get_db)]):
    return db.query(DiagnosticTest).order_by(DiagnosticTest.name).all()


@router.get("/{test_id}", response_model=TestOut, summary="Get a diagnostic test by id")
def get_test(test_id: int, db: Annotated[Session, Depends(get_db)]):
    test = db.get(DiagnosticTest, test_id)
    if test is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    return test


@router.get("/{test_id}/offerings", response_model=list[CentreTestOut],
            summary="List centres offering a test, with each centre's price")
def list_offerings(test_id: int, db: Annotated[Session, Depends(get_db)]):
    test = db.get(DiagnosticTest, test_id)
    if test is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    return (
        db.query(CentreTest)
        .filter(CentreTest.test_id == test_id)
        .order_by(CentreTest.price)
        .all()
    )
