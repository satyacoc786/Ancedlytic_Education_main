import pytest
from unittest.mock import MagicMock
from backend.services.risk_service import analyze_student_risks

def test_academic_risk_separation():
    # Student with poor attendance and low CGPA, but high coding skills
    acad = MagicMock(cgpa=5.2, backlogs=1)
    att = MagicMock(percentage=62.0)
    lms = MagicMock(completion_rate=55.0, assignments_submitted=10, assignments_total=20)
    plc = MagicMock(readiness_score=85.0, aptitude_score=80.0, coding_score=88.0, comm_score=80.0, resume_score=85.0, mock_interviews=3)
    eng = MagicMock(score=75.0)

    res = analyze_student_risks(acad, att, lms, plc, eng)

    assert res["academic_risk"] is True
    assert res["placement_risk"] is False
    assert res["risk_summary_badge"] == "Academic Risk"
    assert len(res["academic_indicators"]) >= 2
    assert len(res["placement_indicators"]) == 0

def test_placement_risk_separation():
    # Student with high CGPA (9.0) and 95% attendance, but low coding and zero mock interviews
    acad = MagicMock(cgpa=9.0, backlogs=0)
    att = MagicMock(percentage=95.0)
    lms = MagicMock(completion_rate=90.0, assignments_submitted=20, assignments_total=20)
    plc = MagicMock(readiness_score=48.0, aptitude_score=45.0, coding_score=40.0, comm_score=55.0, resume_score=50.0, mock_interviews=0)
    eng = MagicMock(score=80.0)

    res = analyze_student_risks(acad, att, lms, plc, eng)

    assert res["academic_risk"] is False
    assert res["placement_risk"] is True
    assert res["risk_summary_badge"] == "Placement Risk"
    assert len(res["placement_indicators"]) >= 2

def test_dual_risk_detection():
    # Student with both academic and placement difficulties
    acad = MagicMock(cgpa=4.5, backlogs=2)
    att = MagicMock(percentage=55.0)
    lms = MagicMock(completion_rate=45.0, assignments_submitted=8, assignments_total=20)
    plc = MagicMock(readiness_score=42.0, aptitude_score=40.0, coding_score=38.0, comm_score=50.0, resume_score=45.0, mock_interviews=0)
    eng = MagicMock(score=40.0)

    res = analyze_student_risks(acad, att, lms, plc, eng)

    assert res["academic_risk"] is True
    assert res["placement_risk"] is True
    assert res["risk_summary_badge"] == "Academic & Placement"

