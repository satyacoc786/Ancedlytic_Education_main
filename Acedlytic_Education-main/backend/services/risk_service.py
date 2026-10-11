from typing import Optional, Any, Dict, List
from backend.config import settings

def analyze_student_risks(
    academic_record: Optional[Any],
    attendance_record: Optional[Any],
    lms_record: Optional[Any],
    placement_record: Optional[Any],
    engagement_record: Optional[Any],
    thresholds: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Transparent rule-based risk detector separating Academic Risk from Placement Risk.
    Provides rule names, actual values, thresholds, severity ratings, and recommended interventions.
    """
    th = {
        "cgpa_min": settings.ACADEMIC_RISK_CGPA_THRESHOLD,       # 6.0
        "att_min": settings.ACADEMIC_RISK_ATTENDANCE_THRESHOLD,   # 75.0
        "lms_min": settings.ACADEMIC_RISK_LMS_THRESHOLD,          # 60.0
        "placement_min": settings.PLACEMENT_RISK_READINESS_THRESHOLD, # 60.0
        "skill_min": settings.PLACEMENT_RISK_SKILL_THRESHOLD      # 55.0
    }
    if thresholds:
        th.update(thresholds)

    academic_indicators: List[Dict[str, Any]] = []
    placement_indicators: List[Dict[str, Any]] = []

    # ================= 1. ACADEMIC RISK RULES =================
    if academic_record:
        cgpa = academic_record.cgpa or 0.0
        backlogs = getattr(academic_record, "backlogs", 0) or 0
        
        # Rule AR-1: Low CGPA
        if cgpa < th["cgpa_min"]:
            severity = "High" if cgpa < 5.0 else "Moderate"
            academic_indicators.append({
                "rule_name": "AR-1: Sub-threshold CGPA",
                "category": "academic",
                "severity": severity,
                "metric_name": "Cumulative Grade Point Average (CGPA)",
                "actual_value": f"{cgpa:.2f} / 10",
                "threshold": f"{th['cgpa_min']:.1f}",
                "reason": f"Current CGPA ({cgpa:.2f}) falls below institutional benchmark ({th['cgpa_min']:.1f}).",
                "recommended_action": "Enroll in department peer-tutoring and review exam answer scripts."
            })
            
        # Rule AR-2: Active Backlogs
        if backlogs > 0:
            severity = "High" if backlogs >= 2 else "Moderate"
            academic_indicators.append({
                "rule_name": "AR-2: Active Backlogs Detected",
                "category": "academic",
                "severity": severity,
                "metric_name": "Active Course Backlogs",
                "actual_value": f"{backlogs} subjects",
                "threshold": "0 backlogs",
                "reason": f"Student has {backlogs} un-cleared backlog course(s) pending re-examination.",
                "recommended_action": "Prioritize remedial backlog classes prior to upcoming semester exam."
            })

    if attendance_record:
        att = attendance_record.percentage or 0.0
        # Rule AR-3: Low Classroom Attendance
        if att < th["att_min"]:
            severity = "High" if att < 60.0 else "Moderate"
            academic_indicators.append({
                "rule_name": "AR-3: Sub-threshold Attendance",
                "category": "academic",
                "severity": severity,
                "metric_name": "Class Attendance Percentage",
                "actual_value": f"{att:.1f}%",
                "threshold": f"{th['att_min']:.1f}%",
                "reason": f"Attendance is {att:.1f}%, below mandatory university requirement of {th['att_min']:.1f}%.",
                "recommended_action": "Issue formal attendance warning and schedule faculty counseling."
            })

    if lms_record:
        comp = lms_record.completion_rate or 0.0
        asgn_pct = (lms_record.assignments_submitted / max(1, lms_record.assignments_total)) * 100.0
        # Rule AR-4: Poor LMS Engagement
        if comp < th["lms_min"] or asgn_pct < 65.0:
            severity = "Moderate" if comp < 50.0 else "Low"
            academic_indicators.append({
                "rule_name": "AR-4: Lagging LMS Course Progress",
                "category": "academic",
                "severity": severity,
                "metric_name": "LMS Course & Assignment Completion",
                "actual_value": f"{comp:.0f}% completion, {asgn_pct:.0f}% assignments",
                "threshold": f"{th['lms_min']:.0f}% course completion",
                "reason": f"Online course engagement ({comp:.0f}%) indicates delayed assignment submissions.",
                "recommended_action": "Send automated assignment reminders and check for LMS login hurdles."
            })

    # ================= 2. PLACEMENT RISK RULES =================
    if placement_record:
        apt = placement_record.aptitude_score or 0.0
        coding = placement_record.coding_score or 0.0
        comm = placement_record.comm_score or 0.0
        resume = placement_record.resume_score or 0.0
        mocks = placement_record.mock_interviews or 0

        # Rule PR-1: Technical Coding Gap
        if coding < th["skill_min"]:
            severity = "High" if coding < 45.0 else "Moderate"
            placement_indicators.append({
                "rule_name": "PR-1: Coding Assessment Skill Gap",
                "category": "placement",
                "severity": severity,
                "metric_name": "Data Structures & Coding Assessment",
                "actual_value": f"{coding:.1f} / 100",
                "threshold": f"{th['skill_min']:.1f}",
                "reason": f"Technical coding test score ({coding:.1f}) is below placement eligibility.",
                "recommended_action": "Assign weekly hands-on coding problem sets and algorithmic lab sessions."
            })

        # Rule PR-2: General Aptitude & Logical Reasoning Gap
        if apt < th["skill_min"]:
            severity = "Moderate"
            placement_indicators.append({
                "rule_name": "PR-2: Quantitative & Aptitude Shortfall",
                "category": "placement",
                "severity": severity,
                "metric_name": "General Aptitude Test",
                "actual_value": f"{apt:.1f} / 100",
                "threshold": f"{th['skill_min']:.1f}",
                "reason": f"Quantitative reasoning score ({apt:.1f}) falls below company screening bar.",
                "recommended_action": "Recommend aptitude prep modules and timed mock entrance tests."
            })

        # Rule PR-3: Incomplete Resume or Mock Interviews
        if resume < 65.0 or mocks < 2:
            severity = "Moderate" if mocks == 0 else "Low"
            placement_indicators.append({
                "rule_name": "PR-3: Incomplete Placement Readiness Milestones",
                "category": "placement",
                "severity": severity,
                "metric_name": "Resume Score & Mock Interview Participation",
                "actual_value": f"Resume: {resume:.0f}%, Mock Interviews: {mocks}",
                "threshold": "Resume >= 65%, Mock Interviews >= 2",
                "reason": "Student has not completed necessary career counseling and mock interview milestones.",
                "recommended_action": "Schedule resume review session with placement cell officers."
            })

    # ================= 3. OVERALL SEVERITY & SUMMARY =================
    has_academic = len(academic_indicators) > 0
    has_placement = len(placement_indicators) > 0

    def get_max_severity(indicators: List[Dict[str, Any]]) -> str:
        if not indicators:
            return "None"
        if any(i["severity"] == "High" for i in indicators):
            return "High"
        if any(i["severity"] == "Moderate" for i in indicators):
            return "Moderate"
        return "Low"

    academic_severity = get_max_severity(academic_indicators)
    placement_severity = get_max_severity(placement_indicators)

    if has_academic and has_placement:
        summary_badge = "Academic & Placement"
    elif has_academic:
        summary_badge = "Academic Risk"
    elif has_placement:
        summary_badge = "Placement Risk"
    else:
        summary_badge = "None"

    return {
        "academic_risk": has_academic,
        "academic_severity": academic_severity,
        "academic_indicators": academic_indicators,
        "placement_risk": has_placement,
        "placement_severity": placement_severity,
        "placement_indicators": placement_indicators,
        "risk_summary_badge": summary_badge
    }

