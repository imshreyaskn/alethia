"""
github.py — GitHub App API routes

GET  /api/github/fetch-file          — test endpoint to verify App auth works
POST /api/github/sync-installations  — syncs GitHub App installations for the logged-in user
"""
from fastapi import APIRouter, HTTPException, Query, Header, Depends
from pydantic import BaseModel
from typing import Optional
import httpx
from app.github.auth import fetch_file_content
from app.db.client import db
from app.core.auth import AuthenticatedUser, get_current_user

router = APIRouter()


class SyncInstallationsRequest(BaseModel):
    provider_token: str


@router.get("/github/fetch-file", tags=["GitHub"])
async def fetch_file(
    repo: str = Query(..., description="owner/repo format, e.g. drizzle-org/realive-test-target"),
    path: str = Query(..., description="File path in repo, e.g. README.md"),
    ref: str  = Query("main", description="Branch or commit SHA"),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Fetches a single file from a GitHub repo using the installed GitHub App.
    
    This proves:
    1. The JWT is being generated correctly from the private key
    2. The App is installed on the target repo
    3. The installation token exchange works
    4. File fetching via the API (not git clone) works
    """
    if repo not in user.allowed_repos:
        raise HTTPException(status_code=403, detail="You do not have access to this repository")
    try:
        content = fetch_file_content(
            repo_full_name=repo,
            file_path=path,
            ref=ref,
        )
        return {
            "repo": repo,
            "path": path,
            "ref": ref,
            "size_bytes": len(content),
            "preview": content[:300] + ("..." if len(content) > 300 else ""),
        }
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/github/sync-installations", tags=["GitHub"])
async def sync_installations(
    req: SyncInstallationsRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Syncs GitHub App installations for the authenticated user.
    
    Called by the frontend after OAuth login. Uses the user's GitHub
    provider_token to fetch their installations from the GitHub API
    and upserts them into the installations table.
    """
    headers = {
        "Authorization": f"Bearer {req.provider_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    async with httpx.AsyncClient() as client:
        inst_res = await client.get(
            "https://api.github.com/user/installations",
            headers=headers,
        )
        if inst_res.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to fetch installations from GitHub: {inst_res.text}",
            )

        data = inst_res.json()
        synced = 0

        for inst in data.get("installations", []):
            inst_id = inst["id"]

            repo_res = await client.get(
                f"https://api.github.com/user/installations/{inst_id}/repositories",
                headers=headers,
            )
            if repo_res.status_code == 200:
                repo_data = repo_res.json()
                repos = [r["full_name"] for r in repo_data.get("repositories", [])]

                db.table("installations").upsert(
                    {
                        "user_id": user.id,
                        "installation_id": inst_id,
                        "repositories": repos,
                    },
                    on_conflict="installation_id",
                ).execute()
                synced += 1

    return {"message": "success", "synced": synced}
