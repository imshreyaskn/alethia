"""
auth.py — Authentication dependency for FastAPI endpoints.

Every protected endpoint uses `Depends(get_current_user)` to:
1. Extract the Bearer token from the Authorization header
2. Validate it against Supabase auth
3. Look up which repos the user has access to via the installations table
"""
from fastapi import Depends, HTTPException, Header
from typing import Optional
from app.db.client import db


class AuthenticatedUser:
    """Holds the verified user's identity and their allowed repositories."""
    def __init__(self, id: str, email: str, user_metadata: dict, allowed_repos: list[str]):
        self.id = id
        self.email = email
        self.user_metadata = user_metadata
        self.allowed_repos = allowed_repos


async def get_current_user(authorization: Optional[str] = Header(None)) -> AuthenticatedUser:
    """
    FastAPI dependency that validates the Supabase JWT from the Authorization header.
    
    Usage:
        @router.get("/runs")
        def list_runs(user: AuthenticatedUser = Depends(get_current_user)):
            # user.id, user.allowed_repos are available
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = authorization.replace("Bearer ", "").strip()
    
    try:
        user_response = db.auth.get_user(token)
        user = user_response.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")
    
    # Look up which repos this user has access to
    try:
        installations = db.table("installations").select("repositories").eq("user_id", user.id).execute()
        allowed_repos = []
        for inst in installations.data:
            repos = inst.get("repositories", [])
            if isinstance(repos, list):
                allowed_repos.extend(repos)
        allowed_repos = list(set(allowed_repos))  # deduplicate
    except Exception:
        allowed_repos = []
    
    return AuthenticatedUser(
        id=user.id,
        email=user.email or "",
        user_metadata=user.user_metadata or {},
        allowed_repos=allowed_repos,
    )
