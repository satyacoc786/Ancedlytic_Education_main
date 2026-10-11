import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from backend.config import settings
from backend.seed import seed_database
from backend.routers import (
    auth_router,
    dashboard_router,
    students_router,
    risks_router,
    placements_router,
    interventions_router,
    integration_router,
    reports_router,
    settings_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB & Seed synthetic cohort if needed
    seed_database(reset=False)
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Full-stack College Analytics Platform for monitoring performance, predicting risk, and coordinating interventions.",
    lifespan=lifespan
)

@app.middleware("http")
async def use_configured_localhost_origin(request, call_next):
    if request.url.hostname == "127.0.0.1" and settings.WEB_AUTHN_RP_ID == "localhost":
        netloc = request.url.netloc.replace("127.0.0.1", "localhost", 1)
        return RedirectResponse(str(request.url.replace(netloc=netloc)), status_code=307)
    return await call_next(request)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(auth_router.router, prefix=settings.API_PREFIX)
app.include_router(dashboard_router.router, prefix=settings.API_PREFIX)
app.include_router(students_router.router, prefix=settings.API_PREFIX)
app.include_router(risks_router.router, prefix=settings.API_PREFIX)
app.include_router(placements_router.router, prefix=settings.API_PREFIX)
app.include_router(interventions_router.router, prefix=settings.API_PREFIX)
app.include_router(integration_router.router, prefix=settings.API_PREFIX)
app.include_router(reports_router.router, prefix=settings.API_PREFIX)
app.include_router(settings_router.router, prefix=settings.API_PREFIX)

# Static root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@app.get("/")
def serve_index():
    index_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Acadivance Smart Campus Analytics API is running"}

@app.get("/staff-dashboard")
def serve_staff_dashboard():
    path = os.path.join(BASE_DIR, "staff-dashboard.html")
    return FileResponse(path)

@app.get("/student-dashboard")
def serve_student_dashboard():
    path = os.path.join(BASE_DIR, "student-dashboard.html")
    return FileResponse(path)

# Mount static files for HTML/CSS/JS assets
app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="static")

