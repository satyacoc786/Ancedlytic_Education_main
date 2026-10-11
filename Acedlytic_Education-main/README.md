# Acadivance — Smart Campus Analytics Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg?style=flat&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Chart.js](https://img.shields.io/badge/Frontend-Chart.js%20&%20Vanilla%20JS-F5788D.svg?style=flat&logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)

Acadivance is a full-stack smart campus analytics platform engineered for faculty, advisors, placement officers, and university leadership to monitor performance, predict student risk early, explain contributing factors, and coordinate timely interventions.

---

## 1. Key Objectives & Capabilities

1. **Predict:** Identifies at-risk students across independent dimensions:
   - **Academic Risk:** Sub-threshold CGPA, course backlogs, low attendance, lagging LMS completion.
   - **Placement Risk:** Technical coding deficits, quantitative aptitude shortfalls, missing mock interviews/resume.
2. **Explain:** Generates transparent, deterministic breakdowns for every student success score ($S$):
   - Component weights & actual point contributions
   - Strongest positive factors and negative risk drivers
   - Documented missing data policy (fair re-weighting without artificial zero penalties)
3. **Improve:** Complete lifecycle management for student interventions:
   - Create, assign, prioritize, track, and close interventions
   - Audit trail tracking who made changes and when
   - Real-time updates reflected immediately in dashboard KPIs

---

## 2. Architecture & Design

```
xl/
├── backend/
│   ├── config.py                 # Application settings, scoring weights, risk thresholds
│   ├── database.py               # SQLAlchemy SQLite engine & session management
│   ├── models.py                 # Relational models: User, Student, Academic, Attendance, LMS, Placement, Intervention, AuditLog
│   ├── schemas.py                # Pydantic validation schemas
│   ├── auth.py                   # PBKDF2-HMAC password hashing, token auth, role authorization
│   ├── seed.py                   # Realistic deterministic seed (140+ students, staff accounts, showcase cohorts)
│   ├── main.py                   # FastAPI root application, CORS, and static file mount
│   ├── services/
│   │   ├── scoring.py            # S = 0.35A + 0.20T + 0.15L + 0.20P + 0.10E explainability engine
│   │   ├── risk_service.py       # Rule-based Academic vs Placement risk detection
│   │   ├── stats_service.py      # Aggregations, KPIs, trends, distributions, segments
│   │   └── csv_service.py        # CSV templates, validation, duplicate check, preview & commit
│   └── routers/
│       ├── auth_router.py        # /api/auth/login, /api/auth/me, /api/auth/logout
│       ├── dashboard_router.py   # /api/dashboard/summary, /api/dashboard/trends
│       ├── students_router.py    # /api/students (list, filter, sort, paginate), /api/students/{id}
│       ├── risks_router.py       # /api/risks (dedicated at-risk student views)
│       ├── placements_router.py  # /api/placements/analytics (skill gaps, readiness comparison)
│       ├── interventions_router.py # /api/interventions (full CRUD + status updates)
│       ├── integration_router.py # /api/integration/template, /api/integration/import
│       ├── reports_router.py     # /api/reports/export.csv, /api/reports/methodology
│       └── settings_router.py    # /api/settings/weights (live weight tuning), /api/settings/audit-logs
├── tests/
│   ├── test_scoring.py           # Formula verification, missing data policy, boundaries
│   ├── test_risks.py             # Academic vs Placement risk separation tests
│   ├── test_auth.py              # Password hashing & token tamper tests
│   └── test_api_integration.py  # End-to-end API integration tests
├── staff-dashboard.html          # Pixel-accurate Staff Dashboard (matching reference UI)
├── staff-dashboard.css           # Acadivance Design System & styling
├── staff-dashboard.js            # Reactive vanilla JS, Chart.js integrations, modals, and CSV handlers
├── student-dashboard.html        # Preserved Student Portal view
├── index.html                    # Unified login portal (Staff, Teacher & Student Login with FRS)
├── style.css                     # Login portal design
├── script.js                     # Login authentication client connecting to FastAPI
├── requirements.txt
├── .env.example
└── README.md
```

---

## 3. Quick Start & Execution

### Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- Web browser (Chrome, Edge, Firefox, Safari)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Seed the Database (Optional if running main.py which auto-seeds)
```bash
python -m backend.seed
```

### Step 3: Run the Application Server
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 4: Open in Your Browser
- **Unified Portal:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/) or [http://127.0.0.1:8000/index.html](http://127.0.0.1:8000/index.html)
- **Staff Dashboard Direct:** [http://127.0.0.1:8000/staff-dashboard.html](http://127.0.0.1:8000/staff-dashboard.html)
- **Student Dashboard Direct:** [http://127.0.0.1:8000/student-dashboard.html](http://127.0.0.1:8000/student-dashboard.html)
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 4. Demo User Accounts

| Role | Username / ID | Password | Portal Destination |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `admin123` | Staff Analytics Dashboard |
| **Faculty / Teacher** | `TCH1042` | `teacher123` | Staff Analytics Dashboard |
| **Faculty Advisor** | `faculty` | `faculty123` | Staff Analytics Dashboard |
| **Placement Officer** | `placement` | `placement123` | Staff Analytics Dashboard |
| **Student (Demo)** | `STU2026001` | `student123` | Student Portal Dashboard |
| **Student (Showcase)** | `CS2021001` | `student123` | Student Portal Dashboard |

Students can enroll Face ID from the Face Sign-in tab after verifying their Student ID and password. Face ID uses the device's platform authenticator (Face ID, Windows Hello, or a passkey); the biometric stays on the device. For local development, open the portal at `http://localhost:8000` so the WebAuthn origin matches.

New students can select **Sign up** on the student portal, create an account with their college-issued ID, and are signed in after registration. This demo does not verify college IDs or email ownership; add institutional verification before using self-registration in production.

Teachers can select **Sign up** in the teacher panel to create an account. Teacher signup grants faculty access to the staff dashboard, so enable this only where open registration is appropriate.

---

## 5. Scoring & Explainability Methodology

### Formula
$$S = 0.35A + 0.20T + 0.15L + 0.20P + 0.10E$$

Where:
- **$A$ (Academic Performance):** Normalized CGPA ($0-10 \to 0-100$), penalized for active backlogs.
- **$T$ (Attendance):** Classroom and laboratory session attendance ($0-100\%$).
- **$L$ (LMS Engagement):** Composite index of course syllabus completion ($45\%$), assignment submissions ($35\%$), and quiz averages ($20\%$).
- **$P$ (Placement & Skills):** Weighted index of coding score ($35\%$), aptitude ($25\%$), soft skills ($20\%$), and resume score ($20\%$).
- **$E$ (Campus Engagement):** Extra-curricular involvement in student clubs, hackathons, and mentor sessions.

### Missing Data Handling Policy
When a data stream is temporarily un-synchronized, the engine **does not assign a 0 penalty**. Instead:
1. It computes a **Data Completeness Index** (e.g., $4/5 \implies 80\%$).
2. It re-normalizes the weights across the available components so the resulting score reflects actual performance fairly.
3. Explicit missing data warnings are highlighted in the student's explainability card.

---

## 6. Running the Automated Test Suite

Run all tests via pytest:
```bash
python -m pytest -v
```

All 16 unit and integration tests will run:
- `test_scoring.py`: Mathematical accuracy, weight contributions, missing data policy, and boundary clamping.
- `test_risks.py`: Separation of Academic vs Placement risk rules and dual-risk detection.
- `test_auth.py`: PBKDF2 hashing, secure token generation, and token tampering resistance.
- `test_api_integration.py`: End-to-end authentication, KPI summaries, student profiling, intervention CRUD, and CSV template downloads.

---

## 7. CSV Import / Export Specifications

The Data Integration module supports CSV uploads for:
- **Students:** `id,name,email,department,semester,academic_year,phone`
- **Academics:** `student_id,cgpa,semester,backlogs,credits_earned`
- **Attendance:** `student_id,percentage,present_days,total_days`
- **LMS Activity:** `student_id,completion_rate,assignments_submitted,assignments_total,quiz_avg`
- **Placement:** `student_id,aptitude_score,coding_score,comm_score,resume_score,mock_interviews,readiness_score`

Templates can be downloaded directly from the **Data Integration** tab or exported via `/api/reports/export.csv`.

