"""Seed a small realistic catalogue: 3 centres, 5 tests, 11 centre-test offerings.

Repeatable: skips rows that already exist (matched by name / centre+test pair),
so it is safe to run more than once. Run with `python -m app.seed`.
"""

from app.core.database import SessionLocal
from app.models.models import CentreTest, DiagnosticCentre, DiagnosticTest

CENTRES = [
    ("Medanta Diagnostics", "Sector 38, Gurugram"),
    ("Dr. Lal PathLabs — HSR Layout", "HSR Layout, Bengaluru"),
    ("Thyrocare Central Processing", "Vashi, Navi Mumbai"),
]

TESTS = [
    ("Complete Blood Count (CBC)",
     "Measures red cells, white cells, and platelets to screen for anaemia and infection."),
    ("Lipid Profile",
     "Cholesterol (HDL/LDL), triglycerides, and total cholesterol for heart-health screening."),
    ("HbA1c",
     "Three-month average blood sugar, used for diabetes monitoring and diagnosis."),
    ("Thyroid Profile (T3, T4, TSH)",
     "Screens thyroid gland function using T3, T4, and TSH hormone levels."),
    ("Vitamin D (25-OH)",
     "Measures vitamin D levels to detect deficiency affecting bones and immunity."),
]

# (centre index into CENTRES, test index into TESTS, price in INR)
OFFERINGS = [
    (0, 0, "299.00"), (0, 1, "799.00"), (0, 2, "549.00"), (0, 3, "449.00"),
    (1, 0, "349.00"), (1, 1, "899.00"), (1, 4, "1099.00"),
    (2, 0, "249.00"), (2, 2, "499.00"), (2, 3, "399.00"), (2, 4, "899.00"),
]


def seed() -> None:
    db = SessionLocal()
    try:
        centres = []
        for name, location in CENTRES:
            centre = db.query(DiagnosticCentre).filter_by(name=name).one_or_none()
            if centre is None:
                centre = DiagnosticCentre(name=name, location=location)
                db.add(centre)
                db.flush()
            centres.append(centre)

        tests = []
        for name, description in TESTS:
            test = db.query(DiagnosticTest).filter_by(name=name).one_or_none()
            if test is None:
                test = DiagnosticTest(name=name, description=description)
                db.add(test)
                db.flush()
            tests.append(test)

        added = 0
        for centre_idx, test_idx, price in OFFERINGS:
            centre, test = centres[centre_idx], tests[test_idx]
            exists = (
                db.query(CentreTest)
                .filter_by(centre_id=centre.id, test_id=test.id)
                .one_or_none()
            )
            if exists is None:
                db.add(CentreTest(centre_id=centre.id, test_id=test.id, price=price))
                added += 1
        db.commit()
        print(f"Seed complete: {len(centres)} centres, {len(tests)} tests, {added} new offerings.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
