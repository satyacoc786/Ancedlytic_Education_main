from typing import Optional, Dict, Any, List
from backend.config import settings

def clamp(val: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    return max(min_val, min(max_val, val))

def calculate_student_success_score(
    academic_record: Optional[Any],
    attendance_record: Optional[Any],
    lms_record: Optional[Any],
    placement_record: Optional[Any],
    engagement_record: Optional[Any],
    custom_weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Computes explainable Student Success Score S = 0.35A + 0.20T + 0.15L + 0.20P + 0.10E
    with missing-data handling, factor contributions, and clear explainability text.
    """
    weights = {
        "academic": settings.WEIGHT_ACADEMIC,
        "attendance": settings.WEIGHT_ATTENDANCE,
        "lms": settings.WEIGHT_LMS,
        "placement": settings.WEIGHT_PLACEMENT,
        "engagement": settings.WEIGHT_ENGAGEMENT,
    }
    if custom_weights:
        weights.update(custom_weights)

    components: Dict[str, Dict[str, Any]] = {}
    missing_notes: List[str] = []
    positive_factors: List[str] = []
    negative_factors: List[str] = []
    recommended_actions: List[str] = []

    # 1. Academic component (A)
    if academic_record and academic_record.cgpa is not None:
        cgpa = academic_record.cgpa
        backlogs = getattr(academic_record, "backlogs", 0) or 0
        raw_score = (cgpa * 10.0) - (backlogs * 5.0)
        norm_score = clamp(raw_score)
        components["academic"] = {
            "raw_value": cgpa,
            "normalized_score": round(norm_score, 1),
            "is_missing": False,
            "description": f"CGPA {cgpa:.2f} / 10 ({backlogs} backlogs)"
        }
        if norm_score >= 75:
            positive_factors.append(f"Strong academic performance with CGPA {cgpa:.2f}")
        elif norm_score < 60:
            negative_factors.append(f"Low CGPA ({cgpa:.2f}) or presence of active backlogs ({backlogs})")
            recommended_actions.append("Schedule academic tutoring and remedial subject support.")
    else:
        components["academic"] = {
            "raw_value": None,
            "normalized_score": 0.0,
            "is_missing": True,
            "description": "Academic records unavailable"
        }
        missing_notes.append("Academic records (CGPA/backlogs) are missing.")

    # 2. Attendance component (T)
    if attendance_record and attendance_record.percentage is not None:
        att = attendance_record.percentage
        norm_score = clamp(att)
        components["attendance"] = {
            "raw_value": att,
            "normalized_score": round(norm_score, 1),
            "is_missing": False,
            "description": f"Classroom attendance: {att:.1f}% ({attendance_record.present_days}/{attendance_record.total_days} days)"
        }
        if norm_score >= 80:
            positive_factors.append(f"Consistent class attendance ({att:.1f}%)")
        elif norm_score < 75:
            negative_factors.append(f"Attendance ({att:.1f}%) is below mandatory threshold of 75%")
            recommended_actions.append("Initiate faculty check-in regarding attendance regularity.")
    else:
        components["attendance"] = {
            "raw_value": None,
            "normalized_score": 0.0,
            "is_missing": True,
            "description": "Attendance record not found"
        }
        missing_notes.append("Attendance records not synced.")

    # 3. LMS engagement component (L)
    if lms_record and lms_record.completion_rate is not None:
        comp = lms_record.completion_rate
        asgn_pct = (lms_record.assignments_submitted / max(1, lms_record.assignments_total)) * 100.0
        quiz = lms_record.quiz_avg or 0.0
        calc_lms = (comp * 0.45) + (asgn_pct * 0.35) + (quiz * 0.20)
        norm_score = clamp(calc_lms)
        components["lms"] = {
            "raw_value": comp,
            "normalized_score": round(norm_score, 1),
            "is_missing": False,
            "description": f"LMS course completion {comp:.1f}%, assignment completion {asgn_pct:.1f}%"
        }
        if norm_score >= 75:
            positive_factors.append(f"High LMS activity: {comp:.1f}% course completion")
        elif norm_score < 60:
            negative_factors.append(f"Low LMS engagement: only {asgn_pct:.1f}% assignments submitted")
            recommended_actions.append("Send LMS assignment reminders and monitor online activity.")
    else:
        components["lms"] = {
            "raw_value": None,
            "normalized_score": 0.0,
            "is_missing": True,
            "description": "LMS activity not synchronized"
        }
        missing_notes.append("LMS engagement data is missing.")

    # 4. Placement & Skills component (P)
    if placement_record and placement_record.readiness_score is not None:
        apt = placement_record.aptitude_score or 0.0
        coding = placement_record.coding_score or 0.0
        comm = placement_record.comm_score or 0.0
        resume = placement_record.resume_score or 0.0
        calc_placement = (apt * 0.25) + (coding * 0.35) + (comm * 0.20) + (resume * 0.20)
        norm_score = clamp(calc_placement)
        components["placement"] = {
            "raw_value": placement_record.readiness_score,
            "normalized_score": round(norm_score, 1),
            "is_missing": False,
            "description": f"Placement readiness: {norm_score:.1f}% (Coding {coding:.0f}, Aptitude {apt:.0f})"
        }
        if norm_score >= 70:
            positive_factors.append(f"Strong placement readiness ({norm_score:.1f}%)")
        elif norm_score < 60:
            negative_factors.append(f"Placement score ({norm_score:.1f}%) is below target readiness")
            recommended_actions.append("Assign technical mock interviews and aptitude workshops.")
    else:
        components["placement"] = {
            "raw_value": None,
            "normalized_score": 0.0,
            "is_missing": True,
            "description": "Placement training data missing"
        }
        missing_notes.append("Placement & skill evaluation data is missing.")

    # 5. Engagement & Participation component (E)
    if engagement_record and engagement_record.score is not None:
        norm_score = clamp(engagement_record.score)
        components["engagement"] = {
            "raw_value": engagement_record.score,
            "normalized_score": round(norm_score, 1),
            "is_missing": False,
            "description": f"Campus involvement: {engagement_record.clubs_count} clubs, {engagement_record.events_attended} events"
        }
        if norm_score >= 70:
            positive_factors.append("Active student engagement in campus clubs & seminars")
        elif norm_score < 50:
            negative_factors.append("Minimal participation in campus co-curricular activities")
            recommended_actions.append("Encourage student to attend department events and mentor sessions.")
    else:
        components["engagement"] = {
            "raw_value": None,
            "normalized_score": 0.0,
            "is_missing": True,
            "description": "Engagement data missing"
        }
        missing_notes.append("Campus engagement indicators not available.")

    # Missing Data Policy:
    # We do NOT treat missing components as zero score.
    # Instead, we compute score dynamically by re-weighting available components.
    available_weight = sum(weights[k] for k, comp in components.items() if not comp["is_missing"])
    data_completeness_pct = (sum(1 for comp in components.values() if not comp["is_missing"]) / len(components)) * 100.0

    if available_weight > 0:
        weighted_sum = sum(
            comp["normalized_score"] * weights[k]
            for k, comp in components.items()
            if not comp["is_missing"]
        )
        overall_score = round(weighted_sum / available_weight, 1)
    else:
        overall_score = 0.0

    # Add weighted contributions to each component output
    for k, comp in components.items():
        comp["weight"] = round(weights[k], 2)
        if comp["is_missing"]:
            comp["weighted_contribution"] = 0.0
        else:
            comp["weighted_contribution"] = round((comp["normalized_score"] * weights[k]), 1)

    # Determine performance band
    if overall_score >= 75.0:
        band = "On Track"
    elif overall_score >= 50.0:
        band = "Needs Attention"
    else:
        band = "At Risk"

    return {
        "overall_score": overall_score,
        "band": band,
        "data_completeness_percent": round(data_completeness_pct, 1),
        "components": components,
        "positive_factors": positive_factors if positive_factors else ["Consistent baseline performance recorded."],
        "negative_factors": negative_factors if negative_factors else ["No major negative risk factors identified."],
        "missing_data_notes": missing_notes,
        "recommended_actions": recommended_actions if recommended_actions else ["Continue periodic academic progress tracking."]
    }

