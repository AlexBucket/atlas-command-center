"""GitHub integration — PRs, issues, commits, workflows via REST API."""

import os
import httpx
from datetime import datetime, timezone

REPOS = ["AlexBucket/atlas-config", "AlexBucket/atlas-command-center"]

# Load GitHub token from file (mounted from host)
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "github_token.txt")
GITHUB_TOKEN = ""
if os.path.exists(TOKEN_PATH):
    with open(TOKEN_PATH) as f:
        GITHUB_TOKEN = f.read().strip()

API_BASE = "https://api.github.com"


async def _gh_get(path: str, params: dict = None) -> dict:
    """Make a GitHub API GET request."""
    if not GITHUB_TOKEN:
        return {"error": "GitHub token not configured"}
    try:
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Atlas-Command-Center/3.0",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{API_BASE}{path}",
                headers=headers,
                params=params,
            )
            if resp.status_code == 200:
                return {"data": resp.json()}
            else:
                return {"error": f"GitHub API {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}


async def get_overview() -> dict:
    """Get an overview of all repos."""
    prs_all = []
    issues_all = []
    for repo in REPOS:
        prs = await _gh_get(f"/repos/{repo}/pulls", {"state": "open", "per_page": 10})
        if "data" in prs:
            for p in prs["data"]:
                p["repo"] = repo
            prs_all.extend(prs["data"])

        issues = await _gh_get(f"/repos/{repo}/issues", {"state": "open", "per_page": 10})
        if "data" in issues:
            for i in issues["data"]:
                if "pull_request" not in i:
                    i["repo"] = repo
                    issues_all.append(i)

    return {
        "repos": REPOS,
        "open_prs": len(prs_all),
        "open_issues": len(issues_all),
        "pull_requests": prs_all,
        "issues": issues_all,
    }


async def get_prs(repo: str = "AlexBucket/atlas-config") -> dict:
    """Get open PRs for a repo."""
    result = await _gh_get(f"/repos/{repo}/pulls", {"state": "open", "per_page": 20})
    if "error" in result:
        return result
    return {"data": result.get("data", []), "repo": repo}


async def get_issues(repo: str = "AlexBucket/atlas-config") -> dict:
    """Get open issues for a repo."""
    result = await _gh_get(f"/repos/{repo}/issues", {"state": "open", "per_page": 20})
    if "error" in result:
        return result
    # Filter out PRs
    items = [i for i in result.get("data", []) if "pull_request" not in i]
    return {"data": items, "repo": repo}


async def get_commits(repo: str = "AlexBucket/atlas-config", limit: int = 10) -> dict:
    """Get recent commits."""
    result = await _gh_get(f"/repos/{repo}/commits", {"per_page": limit})
    if "error" in result:
        return result
    commits = []
    for c in result.get("data", []):
        commits.append({
            "sha": c.get("sha", "")[:8],
            "message": c.get("commit", {}).get("message", "").split("\n")[0],
            "author": c.get("commit", {}).get("author", {}).get("name", ""),
            "date": c.get("commit", {}).get("author", {}).get("date", ""),
        })
    return {"data": commits, "repo": repo}


async def get_workflows(repo: str = "AlexBucket/atlas-config") -> dict:
    """Get recent workflow runs."""
    result = await _gh_get(f"/repos/{repo}/actions/runs", {"per_page": 10})
    if "error" in result:
        return result
    runs = []
    for r in result.get("data", {}).get("workflow_runs", []):
        runs.append({
            "databaseId": r.get("id"),
            "displayTitle": r.get("display_title") or r.get("name", ""),
            "workflowName": r.get("name", ""),
            "status": r.get("status"),
            "conclusion": r.get("conclusion"),
            "createdAt": r.get("created_at"),
            "updatedAt": r.get("updated_at"),
            "headBranch": r.get("head_branch"),
            "url": r.get("html_url"),
        })
    return {"data": runs, "repo": repo}


async def approve_pr(repo: str, pr_number: int) -> dict:
    """Approve a pull request."""
    if not GITHUB_TOKEN:
        return {"error": "GitHub token not configured"}
    try:
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Atlas-Command-Center/3.0",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{API_BASE}/repos/{repo}/pulls/{pr_number}/reviews",
                headers=headers,
                json={"event": "APPROVE", "body": "Approved via Atlas Command Center"},
            )
            if resp.status_code in (200, 201):
                return {"status": "approved", "pr": pr_number, "repo": repo}
            else:
                return {"error": f"GitHub API {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}


async def rerun_workflow(repo: str, run_id: int) -> dict:
    """Rerun a failed workflow run."""
    if not GITHUB_TOKEN:
        return {"error": "GitHub token not configured"}
    try:
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Atlas-Command-Center/3.0",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{API_BASE}/repos/{repo}/actions/runs/{run_id}/rerun",
                headers=headers,
            )
            if resp.status_code == 201:
                return {"status": "rerun_started", "run_id": run_id, "repo": repo}
            else:
                return {"error": f"GitHub API {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}


async def get_repos() -> dict:
    """List all repos."""
    result = await _gh_get("/users/AlexBucket/repos", {"per_page": 20, "sort": "updated"})
    if "error" in result:
        return result
    repos = []
    for r in result.get("data", []):
        repos.append({
            "name": r.get("name"),
            "description": r.get("description"),
            "url": r.get("html_url"),
            "isPrivate": r.get("private", False),
            "updatedAt": r.get("updated_at"),
            "language": r.get("language"),
        })
    return {"data": repos}