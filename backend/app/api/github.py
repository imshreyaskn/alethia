"""
github.py — GitHub App API routes

GET /api/github/fetch-file  — test endpoint to verify App auth works
                              (used in Milestone 2 verification only)
"""
from fastapi import APIRouter, HTTPException, Query
from app.github.auth import fetch_file_content

router = APIRouter()


@router.get("/github/fetch-file", tags=["GitHub"])
async def fetch_file(
    repo: str = Query(..., description="owner/repo format, e.g. drizzle-org/realive-test-target"),
    path: str = Query(..., description="File path in repo, e.g. README.md"),
    ref: str  = Query("main", description="Branch or commit SHA"),
):
    """
    Fetches a single file from a GitHub repo using the installed GitHub App.
    
    This proves:
    1. The JWT is being generated correctly from the private key
    2. The App is installed on the target repo
    3. The installation token exchange works
    4. File fetching via the API (not git clone) works
    """
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
