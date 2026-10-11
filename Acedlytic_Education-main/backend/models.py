import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
)
from sqlalchemy.orm import relationship
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(30), default="faculty", nullable=False) # admin, faculty, placement_officer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    interventions_assigned = relationship("Intervention", back_populates="assignee")

class Student(Base):
    __tablename__ = "students"

    id = Column(String(50), primary_key=True, index=True) # e.g. CS2021001
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    department = Column(String(50), nullable=False) # Computer Science, Electronics, etc.
    semester = Column(Integer, default=6)
    academic_year = Column(String(20), default="2024-2025")
    phone = Column(String(20), nullable=True)
    avatar = Column(String(10), default="S")
    status = Column(String(20), default="Active")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships to data components
    academic = relationship("AcademicRecord", back_populates="student", uselist=False, cascade="all, delete-orphan")
    attendance = relationship("AttendanceRecord", back_populates="student", uselist=False, cascade="all, delete-orphan")
    lms = relationship("LMSEngagement", back_populates="student", uselist=False, cascade="all, delete-orphan")
    placement = relationship("PlacementSkills", back_populates="student", uselist=False, cascade="all, delete-orphan")
    engagement = relationship("EngagementRecord", back_populates="student", uselist=False, cascade="all, delete-orphan")
    interventions = relationship("Intervention", back_populates="student", cascade="all, delete-orphan")

class AcademicRecord(Base):
    __tablename__ = "academic_records"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(50), ForeignKey("students.id"), unique=True, nullable=False)
    cgpa = Column(Float, nullable=False, default=7.0)
    semester = Column(Integer, default=6)
    backlogs = Column(Integer, default=0)
    credits_earned = Column(Integer, default=120)
    subjects_json = Column(Text, default="[]") # JSON array of {name, marks, grade}

    student = relationship("Student", back_populates="academic")

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(50), ForeignKey("students.id"), unique=True, nullable=False)
    percentage = Column(Float, nullable=False, default=75.0)
    present_days = Column(Integer, default=150)
    total_days = Column(Integer, default=200)
    last_date = Column(String(50), default="2025-05-10")

    student = relationship("Student", back_populates="attendance")

class LMSEngagement(Base):
    __tablename__ = "lms_engagements"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(50), ForeignKey("students.id"), unique=True, nullable=False)
    courses_enrolled = Column(Integer, default=6)
    completion_rate = Column(Float, default=70.0) # 0-100%
    assignments_submitted = Column(Integer, default=20)
    assignments_total = Column(Integer, default=24)
    quiz_avg = Column(Float, default=75.0)
    forum_posts = Column(Integer, default=10)
    last_activity = Column(String(50), default="LMS 2 days ago")

    student = relationship("Student", back_populates="lms")

class PlacementSkills(Base):
    __tablename__ = "placement_skills"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(50), ForeignKey("students.id"), unique=True, nullable=False)
    aptitude_score = Column(Float, default=65.0) # 0-100
    coding_score = Column(Float, default=60.0)   # 0-100
    comm_score = Column(Float, default=70.0)     # 0-100
    resume_score = Column(Float, default=75.0)   # 0-100
    mock_interviews = Column(Integer, default=2)
    certifications_count = Column(Integer, default=2)
    readiness_score = Column(Float, default=65.0) # 0-100
    skills_json = Column(Text, default="[]")     # JSON array of {name, level}

    student = relationship("Student", back_populates="placement")

class EngagementRecord(Base):
    __tablename__ = "engagement_records"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(50), ForeignKey("students.id"), unique=True, nullable=False)
    score = Column(Float, default=70.0) # 0-100
    clubs_count = Column(Integer, default=2)
    events_attended = Column(Integer, default=4)
    mentor_meetings = Column(Integer, default=3)
    last_meeting = Column(String(50), default="2025-05-02")

    student = relationship("Student", back_populates="engagement")

class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(50), ForeignKey("students.id"), nullable=False)
    title = Column(String(150), nullable=False)
    category = Column(String(50), nullable=False) # academic, placement, attendance, general
    issue = Column(String(150), nullable=False) # e.g. "Low CGPA", "Attendance Issues"
    action_plan = Column(Text, nullable=False)
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_to_name = Column(String(100), default="Staff Member")
    priority = Column(String(20), default="Medium") # Low, Medium, High, Urgent
    status = Column(String(30), default="Open") # Open, Scheduled, In Progress, Completed, Cancelled
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    due_date = Column(String(50), default="May 25, 2025")
    follow_up_date = Column(String(50), nullable=True)
    notes = Column(Text, default="")
    completed_at = Column(DateTime, nullable=True)

    student = relationship("Student", back_populates="interventions")
    assignee = relationship("User", back_populates="interventions_assigned")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    user_name = Column(String(100), default="System")
    action = Column(String(100), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False)
    value_json = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class WebAuthnCredential(Base):
    __tablename__ = "webauthn_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    credential_id = Column(String(1024), unique=True, nullable=False)
    public_key = Column(Text, nullable=False)
    sign_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class WebAuthnChallenge(Base):
    __tablename__ = "webauthn_challenges"

    challenge = Column(String(256), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    purpose = Column(String(20), nullable=False)
    rp_id = Column(String(255), nullable=False)
    origin = Column(String(512), nullable=False)
    expires_at = Column(DateTime, nullable=False)

