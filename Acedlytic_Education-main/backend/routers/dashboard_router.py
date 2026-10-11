from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.auth import require_role
from backend.database import get_db
from backend.services.ai_coach import generate_teacher_coach_response
from backend.services.stats_service import compute_dashboard_analytics

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class TeacherCoachRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Returns all KPI cards, risk distribution, department stats, segments, review list, and insights."""
    return compute_dashboard_analytics(db)


@router.post("/coach")
def teacher_ai_coach(
    payload: TeacherCoachRequest,
    db: Session = Depends(get_db),
    _current_user=Depends(require_role("faculty")),
):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Please enter a question")
    analytics = compute_dashboard_analytics(db)
    return generate_teacher_coach_response(question, analytics)

@router.get("/trends")
def get_dashboard_trends(timeframe: str = "6months"):
    """Returns 6-month historical/projected student success score trend."""
    return {
        "labels": ["Nov 2024", "Dec 2024", "Jan 2025", "Feb 2025", "Mar 2025", "Apr 2025"],
        "scores": [51.5, 56.2, 60.8, 65.4, 69.8, 73.6],
        "target": 75.0
    }

