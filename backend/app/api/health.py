"""
health.py — Health check endpoint.

Verifies the server is alive AND the Supabase database is reachable.
This is the Milestone 1 version — it actually runs a DB query.
"""
from fastapi import APIRouter
from app.db.client import db

router = APIRouter()


@router.get("/health", tags=["System"])
async def health_check():
    """
    Returns the health status of the backend and database connection.
    
    DB check: runs a lightweight COUNT query on pipeline_runs.
    If Supabase is unreachable or misconfigured, 'db' returns 'disconnected'
    with an error message — the server keeps running either way.
    """
    db_status = "disconnected"
    db_error = None

    try:
        # Lightweight query: just count rows (returns 0 on empty table, that's fine)
        result = db.table("pipeline_runs").select("id", count="exact").limit(1).execute()
        db_status = "connected"
    except Exception as e:
        db_error = str(e)

    return {
        "status": "ok",
        "service": "realive-backend",
        "db": db_status,
        **({"db_error": db_error} if db_error else {}),
    }
