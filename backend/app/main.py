"""
main.py — FastAPI application entry point.

WHAT IS FASTAPI?
FastAPI is a Python web framework. It turns Python functions into HTTP
endpoints and handles request parsing, validation, and response serialization
automatically. It's also async-native — meaning it can handle many
simultaneous connections efficiently without blocking.

HOW TO RUN:
  uvicorn app.main:app --reload --port 8000

  - 'app.main' = the module path (backend/app/main.py)
  - 'app'      = the FastAPI() instance variable name
  - '--reload' = auto-restart on file changes (dev only)
"""
import sys
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.health import router as health_router
from app.api.github import router as github_router
from app.api.webhook import router as webhook_router
from app.api.runs import router as runs_router

# --- App Instance ---
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Assisted CI/CD Test Repair Platform",
    version="0.1.0",
    docs_url="/docs",   # Swagger UI auto-generated at http://localhost:8000/docs
    redoc_url="/redoc",
)

# --- CORS Middleware ---
# CORS (Cross-Origin Resource Sharing): browsers block requests from one
# origin (e.g. localhost:5173) to another (localhost:8000) by default.
# This tells the backend to allow the React frontend to talk to it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()],

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register Routers ---
# Routers are groups of related endpoints. We add a prefix so every
# health route becomes /api/health, etc.
app.include_router(health_router,  prefix="/api")
app.include_router(github_router,  prefix="/api")
app.include_router(webhook_router, prefix="/api")
app.include_router(runs_router,    prefix="/api")

# Future routers (added in later milestones):
# app.include_router(webhook_router, prefix="/api")
# app.include_router(runs_router, prefix="/api")
