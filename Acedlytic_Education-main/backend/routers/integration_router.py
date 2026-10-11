from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Response
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.services.csv_service import get_csv_template, parse_and_validate_csv
from backend.auth import get_current_user
from backend.models import AuditLog

router = APIRouter(prefix="/integration", tags=["Data Integration"])

@router.get("/template/{import_type}")
def download_template(import_type: str):
    template = get_csv_template(import_type.lower())
    return Response(
        content=template,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=template_{import_type}.csv"}
    )

@router.post("/import")
async def import_csv_file(
    import_type: str = Form(...),
    commit: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files (.csv) are accepted.")

    content = await file.read()
    try:
        csv_text = content.decode("utf-8-sig") # handles UTF-8 BOM
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file encoding. Please provide UTF-8 encoded CSV.")

    res = parse_and_validate_csv(csv_text, import_type=import_type.lower(), db=db, commit=commit)

    if commit and res["valid_rows"] > 0:
        log = AuditLog(
            user_id=current_user.id,
            user_name=current_user.full_name,
            action="CSV_IMPORT",
            target_type=import_type.upper(),
            details=f"Imported {res['valid_rows']} rows of {import_type} data from {file.filename}"
        )
        db.add(log)
        db.commit()

    return res

