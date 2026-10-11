import random
import json
import datetime
from sqlalchemy.orm import Session
from backend.database import SessionLocal, Base, engine
from backend.models import (
    User, Student, AcademicRecord, AttendanceRecord, LMSEngagement,
    PlacementSkills, EngagementRecord, Intervention, AuditLog
)
from backend.auth import hash_password

DEPTS = [
    ("Computer Science", "CS", 198),
    ("Electronics", "EC", 142),
    ("Mechanical", "ME", 121),
    ("Civil", "CE", 98),
    ("Business", "BA", 87),
    ("Biotech", "BT", 64),
    ("Others", "OT", 132),
]

FIRST_NAMES = [
    "Aarav", "Priya", "Rohit", "Sneha", "Vikram", "Ananya", "Karan", "Pooja", "Rahul", "Neha",
    "Aditya", "Riya", "Varun", "Tanvi", "Siddharth", "Ishita", "Arjun", "Kavya", "Manish", "Divya",
    "Nikhil", "Shreya", "Deepak", "Meera", "Abhishek", "Swati", "Gaurav", "Pallavi", "Pranav", "Bhavna",
    "Harsh", "Simran", "Yash", "Anushka", "Rohan", "Sonal", "Kunal", "Tanya", "Akash", "Aishwarya"
]

LAST_NAMES = [
    "Sharma", "Nair", "Kumar", "Iyer", "Singh", "Patel", "Gupta", "Rao", "Verma", "Mehta",
    "Reddy", "Joshi", "Chopra", "Bose", "Menon", "Kapoor", "Mishra", "Deshmukh", "Pandey", "Kulkarni"
]

def ensure_student_accounts(db: Session):
    existing_usernames = {username for (username,) in db.query(User.username).all()}
    for student in db.query(Student).all():
        if student.id in existing_usernames:
            continue
        db.add(User(
            username=student.id,
            email=student.email,
            hashed_password=hash_password("student123"),
            full_name=student.name,
            role="student"
        ))

def seed_database(reset: bool = False):
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        if db.query(User).first() and not reset:
            ensure_student_accounts(db)
            db.commit()
            print("Database already has records. Skipping seed.")
            return

        print("Seeding database with demo users, 120+ synthetic students, and interventions...")

        # 1. Staff Demo Accounts
        staff_users = [
            User(
                username="admin",
                email="admin@college.edu",
                hashed_password=hash_password("admin123"),
                full_name="Staff User",
                role="admin"
            ),
            User(
                username="TCH1042",
                email="tch1042@college.edu",
                hashed_password=hash_password("teacher123"),
                full_name="Dr. Mehta",
                role="faculty"
            ),
            User(
                username="faculty",
                email="faculty@college.edu",
                hashed_password=hash_password("faculty123"),
                full_name="Prof. Rao",
                role="faculty"
            ),
            User(
                username="placement",
                email="placement@college.edu",
                hashed_password=hash_password("placement123"),
                full_name="Ms. Kapoor",
                role="placement_officer"
            ),
        ]
        for u in staff_users:
            db.add(u)
        db.flush()

        # 2. Key Showcase Students (from Reference Image)
        key_students = [
            {
                "id": "CS2021001", "name": "Aarav Sharma", "dept": "Computer Science",
                "cgpa": 4.8, "backlogs": 2, "att": 58.0, "lms_comp": 40.0, "last_act": "LMS 3 days ago",
                "coding": 38.0, "apt": 44.0, "comm": 52.0, "resume": 45.0, "mocks": 0, "readiness": 42.0,
                "eng_score": 40.0, "clubs": 0, "events": 1, "mentor": 1
            },
            {
                "id": "EC2021042", "name": "Priya Nair", "dept": "Electronics",
                "cgpa": 7.4, "backlogs": 0, "att": 82.0, "lms_comp": 75.0, "last_act": "Attendance 2 days ago",
                "coding": 46.0, "apt": 48.0, "comm": 65.0, "resume": 55.0, "mocks": 1, "readiness": 52.0,
                "eng_score": 68.0, "clubs": 2, "events": 3, "mentor": 2
            },
            {
                "id": "ME2021076", "name": "Rohit Kumar", "dept": "Mechanical",
                "cgpa": 5.8, "backlogs": 1, "att": 66.0, "lms_comp": 55.0, "last_act": "Exam 5 days ago",
                "coding": 68.0, "apt": 70.0, "comm": 62.0, "resume": 72.0, "mocks": 2, "readiness": 68.0,
                "eng_score": 65.0, "clubs": 1, "events": 2, "mentor": 2
            },
            {
                "id": "CS2021108", "name": "Sneha Iyer", "dept": "Computer Science",
                "cgpa": 6.2, "backlogs": 1, "att": 71.0, "lms_comp": 60.0, "last_act": "LMS 1 day ago",
                "coding": 75.0, "apt": 72.0, "comm": 74.0, "resume": 76.0, "mocks": 2, "readiness": 74.0,
                "eng_score": 70.0, "clubs": 2, "events": 4, "mentor": 3
            },
            {
                "id": "CE2021133", "name": "Vikram Singh", "dept": "Civil",
                "cgpa": 7.2, "backlogs": 0, "att": 80.0, "lms_comp": 72.0, "last_act": "Attendance 3 days ago",
                "coding": 44.0, "apt": 46.0, "comm": 58.0, "resume": 50.0, "mocks": 0, "readiness": 49.0,
                "eng_score": 60.0, "clubs": 1, "events": 2, "mentor": 1
            },
            {
                "id": "STU2026001", "name": "Rohan Deshmukh", "dept": "Computer Science",
                "cgpa": 8.4, "backlogs": 0, "att": 88.0, "lms_comp": 85.0, "last_act": "LMS today",
                "coding": 88.0, "apt": 82.0, "comm": 85.0, "resume": 90.0, "mocks": 3, "readiness": 86.0,
                "eng_score": 85.0, "clubs": 3, "events": 6, "mentor": 4
            }
        ]

        created_ids = set()

        for ks in key_students:
            created_ids.add(ks["id"])
            s = Student(
                id=ks["id"],
                name=ks["name"],
                email=f"{ks['id'].lower()}@college.edu",
                department=ks["dept"],
                semester=6,
                academic_year="2024-2025",
                phone="+91-98" + str(random.randint(10000000, 99999999)),
                avatar=ks["name"][0]
            )
            db.add(s)

            subjs = [
                {"name": "Core Subject I", "marks": int(ks["cgpa"] * 9.5), "grade": "B"},
                {"name": "Core Subject II", "marks": int(ks["cgpa"] * 9.2), "grade": "B"},
                {"name": "Lab Practical", "marks": int(ks["cgpa"] * 10), "grade": "A"}
            ]
            db.add(AcademicRecord(
                student_id=ks["id"],
                cgpa=ks["cgpa"],
                semester=6,
                backlogs=ks["backlogs"],
                credits_earned=120,
                subjects_json=json.dumps(subjs)
            ))

            db.add(AttendanceRecord(
                student_id=ks["id"],
                percentage=ks["att"],
                present_days=int(ks["att"] * 2),
                total_days=200
            ))

            db.add(LMSEngagement(
                student_id=ks["id"],
                courses_enrolled=6,
                completion_rate=ks["lms_comp"],
                assignments_submitted=int(ks["lms_comp"] * 0.24),
                assignments_total=24,
                quiz_avg=ks["lms_comp"] + random.randint(-5, 5),
                last_activity=ks["last_act"]
            ))

            skills = [
                {"name": "Python / Java", "level": ks["coding"]},
                {"name": "Quantitative Aptitude", "level": ks["apt"]},
                {"name": "Communication", "level": ks["comm"]}
            ]
            db.add(PlacementSkills(
                student_id=ks["id"],
                aptitude_score=ks["apt"],
                coding_score=ks["coding"],
                comm_score=ks["comm"],
                resume_score=ks["resume"],
                mock_interviews=ks["mocks"],
                certifications_count=random.randint(1, 3),
                readiness_score=ks["readiness"],
                skills_json=json.dumps(skills)
            ))

            db.add(EngagementRecord(
                student_id=ks["id"],
                score=ks["eng_score"],
                clubs_count=ks["clubs"],
                events_attended=ks["events"],
                mentor_meetings=ks["mentor"]
            ))

        # 3. Generate remaining realistic synthetic student cohort (up to ~140 students)
        random.seed(42) # Deterministic realistic seed
        dept_dist = [
            ("Computer Science", "CS", 38),
            ("Electronics", "EC", 28),
            ("Mechanical", "ME", 24),
            ("Civil", "CE", 18),
            ("Business", "BA", 16),
            ("Biotech", "BT", 12),
            ("Others", "OT", 14),
        ]

        counter = 200
        for dept_name, prefix, count in dept_dist:
            for _ in range(count):
                counter += 1
                sid = f"{prefix}2021{counter:03d}"
                if sid in created_ids:
                    continue
                created_ids.add(sid)

                fn = random.choice(FIRST_NAMES)
                ln = random.choice(LAST_NAMES)
                full_name = f"{fn} {ln}"
                sem = random.choice([4, 5, 6, 7, 8])

                # Risk distribution archetype
                archetype = random.random()
                if archetype < 0.10: # Both Risks
                    cgpa = round(random.uniform(4.5, 5.8), 2)
                    backlogs = random.choice([1, 2, 3])
                    att = round(random.uniform(52.0, 70.0), 1)
                    lms_comp = round(random.uniform(40.0, 58.0), 1)
                    coding = round(random.uniform(35.0, 50.0), 1)
                    apt = round(random.uniform(40.0, 52.0), 1)
                    comm = round(random.uniform(45.0, 60.0), 1)
                    resume = round(random.uniform(40.0, 60.0), 1)
                    mocks = random.choice([0, 1])
                    readiness = round(random.uniform(40.0, 54.0), 1)
                    eng_sc = round(random.uniform(35.0, 55.0), 1)
                elif archetype < 0.22: # Academic Risk only
                    cgpa = round(random.uniform(5.0, 5.9), 2)
                    backlogs = random.choice([1, 2])
                    att = round(random.uniform(55.0, 72.0), 1)
                    lms_comp = round(random.uniform(45.0, 62.0), 1)
                    coding = round(random.uniform(65.0, 85.0), 1)
                    apt = round(random.uniform(65.0, 80.0), 1)
                    comm = round(random.uniform(65.0, 80.0), 1)
                    resume = round(random.uniform(70.0, 85.0), 1)
                    mocks = random.choice([2, 3])
                    readiness = round(random.uniform(65.0, 80.0), 1)
                    eng_sc = round(random.uniform(60.0, 75.0), 1)
                elif archetype < 0.32: # Placement Risk only
                    cgpa = round(random.uniform(7.2, 8.8), 2)
                    backlogs = 0
                    att = round(random.uniform(80.0, 95.0), 1)
                    lms_comp = round(random.uniform(75.0, 95.0), 1)
                    coding = round(random.uniform(38.0, 52.0), 1)
                    apt = round(random.uniform(42.0, 54.0), 1)
                    comm = round(random.uniform(50.0, 65.0), 1)
                    resume = round(random.uniform(45.0, 62.0), 1)
                    mocks = random.choice([0, 1])
                    readiness = round(random.uniform(45.0, 58.0), 1)
                    eng_sc = round(random.uniform(55.0, 70.0), 1)
                else: # Good / On track
                    cgpa = round(random.uniform(7.5, 9.4), 2)
                    backlogs = 0
                    att = round(random.uniform(82.0, 98.0), 1)
                    lms_comp = round(random.uniform(75.0, 98.0), 1)
                    coding = round(random.uniform(70.0, 95.0), 1)
                    apt = round(random.uniform(70.0, 92.0), 1)
                    comm = round(random.uniform(72.0, 92.0), 1)
                    resume = round(random.uniform(75.0, 95.0), 1)
                    mocks = random.choice([2, 3, 4])
                    readiness = round(random.uniform(72.0, 94.0), 1)
                    eng_sc = round(random.uniform(70.0, 95.0), 1)

                activities = [
                    "LMS 1 day ago", "LMS 2 days ago", "Attendance yesterday",
                    "Attendance 2 days ago", "Exam 3 days ago", "Assessment submitted"
                ]

                s = Student(
                    id=sid,
                    name=full_name,
                    email=f"{sid.lower()}@college.edu",
                    department=dept_name,
                    semester=sem,
                    academic_year="2024-2025",
                    phone="+91-98" + str(random.randint(10000000, 99999999)),
                    avatar=fn[0]
                )
                db.add(s)

                subjs = [
                    {"name": f"{dept_name} Module A", "marks": int(cgpa * 9.8), "grade": "A" if cgpa > 8 else "B"},
                    {"name": f"{dept_name} Module B", "marks": int(cgpa * 9.5), "grade": "B"},
                    {"name": "Laboratory Session", "marks": int(cgpa * 10), "grade": "A"}
                ]
                db.add(AcademicRecord(
                    student_id=sid,
                    cgpa=cgpa,
                    semester=sem,
                    backlogs=backlogs,
                    credits_earned=120,
                    subjects_json=json.dumps(subjs)
                ))

                db.add(AttendanceRecord(
                    student_id=sid,
                    percentage=att,
                    present_days=int(att * 2),
                    total_days=200
                ))

                db.add(LMSEngagement(
                    student_id=sid,
                    courses_enrolled=6,
                    completion_rate=lms_comp,
                    assignments_submitted=int(lms_comp * 0.24),
                    assignments_total=24,
                    quiz_avg=round(lms_comp + random.uniform(-4, 4), 1),
                    last_activity=random.choice(activities)
                ))

                skills = [
                    {"name": "Domain Skills", "level": coding},
                    {"name": "Aptitude & Logic", "level": apt},
                    {"name": "Soft Skills", "level": comm}
                ]
                db.add(PlacementSkills(
                    student_id=sid,
                    aptitude_score=apt,
                    coding_score=coding,
                    comm_score=comm,
                    resume_score=resume,
                    mock_interviews=mocks,
                    certifications_count=random.randint(1, 4),
                    readiness_score=readiness,
                    skills_json=json.dumps(skills)
                ))

                db.add(EngagementRecord(
                    student_id=sid,
                    score=eng_sc,
                    clubs_count=random.randint(0, 3),
                    events_attended=random.randint(1, 5),
                    mentor_meetings=random.randint(1, 4)
                ))

        db.flush()

        ensure_student_accounts(db)

        # 4. Seed Showcase Interventions (Matching reference dashboard exactly)
        interventions = [
            Intervention(
                student_id="CS2021001",
                title="Academic Remediation & CGPA Recovery",
                category="academic",
                issue="Low CGPA",
                action_plan="Weekly remedial tutoring sessions in Data Structures and regular progress review.",
                assigned_to_name="Dr. Mehta",
                priority="High",
                status="In Progress",
                due_date="May 20, 2025",
                notes="Student attended introductory counseling session."
            ),
            Intervention(
                student_id="EC2021042",
                title="Placement Readiness & Mock Interview Coaching",
                category="placement",
                issue="Placement Readiness",
                action_plan="Schedule resume restructuring session and pair with placement student mentor.",
                assigned_to_name="Ms. Kapoor",
                priority="Medium",
                status="Scheduled",
                due_date="May 25, 2025",
                notes="Mock interview scheduled for May 23."
            ),
            Intervention(
                student_id="ME2021076",
                title="Class Attendance Follow-up & Advisory",
                category="attendance",
                issue="Attendance Issues",
                action_plan="Parent communication and formal attendance commitment contract.",
                assigned_to_name="Mr. Rao",
                priority="High",
                status="Open",
                due_date="May 22, 2025",
                notes="Attendance dropped below 68% in recent three weeks."
            ),
            Intervention(
                student_id="CS2021108",
                title="Exam Performance Assessment Check-in",
                category="academic",
                issue="Exam Performance",
                action_plan="Review midterm answer sheets and provide sample question bank.",
                assigned_to_name="Dr. Sharma",
                priority="Medium",
                status="In Progress",
                due_date="May 18, 2025",
                notes="Midterm exam marks discussed."
            ),
            Intervention(
                student_id="CE2021133",
                title="Technical Aptitude Preparation Course",
                category="placement",
                issue="Skill Gap in Coding",
                action_plan="Enroll in technical boot camp modules on core reasoning.",
                assigned_to_name="Ms. Kapoor",
                priority="Low",
                status="Scheduled",
                due_date="May 28, 2025",
                notes="Assigned online practice set 1."
            ),
        ]
        for it in interventions:
            db.add(it)

        # 5. Seed Initial Audit Log Entries
        audit_entries = [
            AuditLog(user_name="System", action="SYSTEM_INIT", target_type="SYSTEM", details="Database initialized and seeded with synthetic student records"),
            AuditLog(user_name="Dr. Mehta", action="CREATE_INTERVENTION", target_type="INTERVENTION", details="Created High Priority intervention for Aarav Sharma"),
            AuditLog(user_name="Ms. Kapoor", action="SCHEDULE_WORKSHOP", target_type="PLACEMENT", details="Created placement training plan for Electronics cohort"),
        ]
        for a in audit_entries:
            db.add(a)

        db.commit()
        print("Database seed complete! Over 140 synthetic records populated.")

    finally:
        db.close()

if __name__ == "__main__":
    seed_database(reset=True)

