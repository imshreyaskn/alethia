"""
auth.py — GitHub App Authentication

HOW GITHUB APP AUTH WORKS (the full flow):

  1. JWT (JSON Web Token): We sign a short-lived token (10 min max) using our
     App's private key. This proves to GitHub "I am App #3825549".

  2. Installation Token: We exchange the JWT for an "installation access token"
     tied to a specific repo installation. This is the actual token we use
     for API calls (fetch files, open PRs, etc.). It expires in 1 hour.

  Why two steps? The JWT identifies the App. The installation token scopes
  access to a specific repo where the app is installed. This means the app
  can only touch repos where a user explicitly installed it — not all repos.

ANALOGY:
  JWT = your employee badge (proves who you are)
  Installation token = a temporary access card for a specific floor (scoped access)
"""
import time
import base64

import jwt
from github import Github, GithubIntegration

from app.core.config import settings


def _get_private_key() -> str:
    """
    Reads and normalises the private key from settings.
    The key is stored in .env as a single line with \\n escape sequences.
    We convert those back to real newlines so PyJWT can parse the PEM.
    """
    key = settings.GITHUB_APP_PRIVATE_KEY
    # Replace literal \n strings with actual newline characters
    return key.replace("\\n", "\n")


def get_installation_token(repo_full_name: str) -> str:
    """
    Given a repo like "drizzle-org/realive-test-target", returns a short-lived
    installation access token that can be used to call the GitHub API for that repo.

    This is the ONLY function the rest of the backend needs to call.
    It handles the full JWT → Installation ID → Token flow internally.

    Args:
        repo_full_name: "owner/repo" format, e.g. "drizzle-org/realive-test-target"

    Returns:
        A string access token, valid for ~1 hour.

    Raises:
        ValueError: if the app is not installed on the given repo.
    """
    private_key = _get_private_key()
    app_id = int(settings.GITHUB_APP_ID)

    # GithubIntegration handles the JWT generation and installation lookup
    integration = GithubIntegration(
        integration_id=app_id,
        private_key=private_key,
    )

    # Find the installation ID for this specific repo
    # (An "installation" = the app being installed on one repo/org)
    try:
        installation = integration.get_repo_installation(
            owner=repo_full_name.split("/")[0],
            repo=repo_full_name.split("/")[1],
        )
    except Exception as e:
        raise ValueError(
            f"GitHub App is not installed on '{repo_full_name}'. "
            f"Go to your GitHub App settings and install it on that repo. "
            f"Original error: {e}"
        )

    # Exchange the installation ID for an access token
    token = integration.get_access_token(installation.id)
    return token.token


def get_github_client(repo_full_name: str) -> Github:
    """
    Returns a fully authenticated PyGitHub client scoped to a specific repo.
    Use this when you need to make multiple API calls — it reuses the token.

    Example usage:
        gh = get_github_client("owner/my-repo")
        repo = gh.get_repo("owner/my-repo")
        file = repo.get_contents("tests/test_orders.py", ref="abc123sha")
    """
    token = get_installation_token(repo_full_name)
    return Github(token)


def fetch_file_content(repo_full_name: str, file_path: str, ref: str) -> str:
    """
    Fetches the raw text content of a single file from a GitHub repo.

    This is used in Phase 1 (Ingestion) to pull the failing test file and
    the source file it imports — without cloning the entire repository.

    Args:
        repo_full_name: "owner/repo"
        file_path:      Path to the file, e.g. "tests/test_orders.py"
        ref:            Git SHA or branch name, e.g. "abc123" or "main"

    Returns:
        The file content as a plain string.

    Raises:
        FileNotFoundError: if the file doesn't exist at that ref.
        ValueError: if the app isn't installed on the repo.
    """
    gh = get_github_client(repo_full_name)
    repo = gh.get_repo(repo_full_name)

    try:
        contents = repo.get_contents(file_path, ref=ref)
        # GitHub returns content as base64-encoded bytes — decode to string
        return base64.b64decode(contents.content).decode("utf-8")
    except Exception as e:
        raise FileNotFoundError(
            f"Could not fetch '{file_path}' at ref '{ref}' "
            f"from '{repo_full_name}': {e}"
        )
