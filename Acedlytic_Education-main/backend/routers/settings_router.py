from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.config import settings
from backend.schemas import ScoringWeightsConfig
from backend.models import AuditLog
from backend.auth import get_current_user

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("/weights")
def get_weights():
    return {
        "weight_academic": settings.WEIGHT_ACADEMIC,
        "weight_attendance": settings.WEIGHT_ATTENDANCE,
        "weight_lms": settings.WEIGHT_LMS,
        "weight_placement": settings.WEIGHT_PLACEMENT,
        "weight_engagement": settings.WEIGHT_ENGAGEMENT,
        "academic_risk_cgpa": settings.ACADEMIC_RISK_CGPA_THRESHOLD,
        "academic_risk_attendance": settings.ACADEMIC_RISK_ATTENDANCE_THRESHOLD,
        "academic_risk_lms": settings.ACADEMIC_RISK_LMS_THRESHOLD,
        "placement_risk_readiness": settings.PLACEMENT_RISK_READINESS_THRESHOLD,
        "placement_risk_skill": settings.PLACEMENT_RISK_SKILL_THRESHOLD
    }

@router.put("/weights")
def update_weights(
    cfg: ScoringWeightsConfig,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    total_w = cfg.weight_academic + cfg.weight_attendance + cfg.weight_lms + cfg.weight_placement + cfg.weight_engagement
    if not (0.95 <= total_w <= 1.05):
        raise HTTPException(status_code=400, detail=f"Sum of weights must equal 1.0 (currently {total_w:.2f})")

    settings.WEIGHT_ACADEMIC = cfg.weight_academic
    settings.WEIGHT_ATTENDANCE = cfg.weight_attendance
    settings.WEIGHT_LMS = cfg.weight_lms
    settings.WEIGHT_PLACEMENT = cfg.weight_placement
    settings.WEIGHT_ENGAGEMENT = cfg.weight_engagement

    settings.ACADEMIC_RISK_CGPA_THRESHOLD = cfg.academic_risk_cgpa
    settings.ACADEMIC_RISK_ATTENDANCE_THRESHOLD = cfg.academic_risk_attendance
    settings.ACADEMIC_RISK_LMS_THRESHOLD = cfg.academic_risk_lms
    settings.PLACEMENT_RISK_READINESS_THRESHOLD = cfg.placement_risk_readiness
    settings.PLACEMENT_RISK_SKILL_THRESHOLD = cfg.placement_risk_skill

    log = AuditLog(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="UPDATE_SETTINGS",
        target_type="SYSTEM_SETTINGS",
        details="Updated student success score weights and institutional risk thresholds"
    )
    db.add(log)
    db.commit()

    return {"message": "Settings updated successfully"}

@router.get("/audit-logs")
def get_audit_logs(db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(25).all()
    return [
        {
            "id": l.id,
            "user_name": l.user_name,
            "action": l.action,
            "target_type": l.target_type,
            "target_id": l.target_id,
            "details": l.details,
            "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }
        for l in logs
    ]

