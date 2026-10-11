import pytest
from unittest.mock import MagicMock
from backend.services.scoring import calculate_student_success_score

def test_scoring_formula_baseline():
    acad = MagicMock(cgpa=8.0, backlogs=0) # 80 norm
    att = MagicMock(percentage=90.0, present_days=180, total_days=200) # 90 norm
    lms = MagicMock(completion_rate=80.0, assignments_submitted=20, assignments_total=20, quiz_avg=80.0) # 80 norm
    plc = MagicMock(readiness_score=80.0, aptitude_score=80.0, coding_score=80.0, comm_score=80.0, resume_score=80.0) # 80 norm
    eng = MagicMock(score=80.0, clubs_count=2, events_attended=4, mentor_meetings=3) # 80 norm

    res = calculate_student_success_score(acad, att, lms, plc, eng)

    # acad=80 (weight 0.35 => 28), att=90 (weight 0.20 => 18),
    # lms=(80*0.45 + 100*0.35 + 80*0.20)=87 (weight 0.15 => 13.05),
    # plc=(80*0.25 + 80*0.35 + 80*0.20 + 80*0.20)=80 (weight 0.20 => 16),
    # eng=80 (weight 0.10 => 8)
    # Sum = 28 + 18 + 13.05 + 16 + 8 = 83.05 -> round to 83.0
    assert res["overall_score"] == 83.0
    assert res["band"] == "On Track"
    assert res["data_completeness_percent"] == 100.0
    assert len(res["positive_factors"]) > 0

def test_missing_data_reweighting():
    # Only academic and attendance present (sum of weights = 0.35 + 0.20 = 0.55)
    acad = MagicMock(cgpa=7.0, backlogs=0) # 70 norm
    att = MagicMock(percentage=80.0, present_days=160, total_days=200) # 80 norm

    res = calculate_student_success_score(acad, att, None, None, None)

    # Weighted sum = 70*0.35 + 80*0.20 = 24.5 + 16.0 = 40.5
    # Scaled to available weight 0.55 => 40.5 / 0.55 = 73.6
    assert res["data_completeness_percent"] == 40.0 # 2 out of 5
    assert len(res["missing_data_notes"]) == 3
    assert 73.0 <= res["overall_score"] <= 74.0

def test_score_boundaries():
    # Extreme values clamped between 0 and 100
    acad = MagicMock(cgpa=15.0, backlogs=0)
    att = MagicMock(percentage=150.0, present_days=300, total_days=200)
    lms = MagicMock(completion_rate=200.0, assignments_submitted=50, assignments_total=20, quiz_avg=120.0)
    plc = MagicMock(readiness_score=150.0, aptitude_score=150.0, coding_score=150.0, comm_score=150.0, resume_score=150.0)
    eng = MagicMock(score=150.0, clubs_count=10, events_attended=10, mentor_meetings=10)

    res = calculate_student_success_score(acad, att, lms, plc, eng)
    assert res["overall_score"] <= 100.0
