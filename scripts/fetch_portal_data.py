"""
fetch_portal_data.py

Fetches real data from GitHub and (optionally) Jira, then writes
portal-live/data/portal-data.json for the APEX SDLC live portal.

Environment variables (all optional):
    GITHUB_TOKEN       - GitHub PAT or Actions token
    GITHUB_REPO        - e.g. "suplab/apex-sdlc"
    JIRA_BASE_URL      - e.g. "https://myorg.atlassian.net"
    JIRA_EMAIL         - Jira user email
    JIRA_API_TOKEN     - Jira API token
    JIRA_BOARD_ID      - numeric Jira board ID
    OUTPUT_PATH        - defaults to "portal-live/data/portal-data.json"
"""

import json
import os
import sys
from datetime import datetime, timezone

import requests


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def github_headers(token: str) -> dict:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def jira_auth(email: str, api_token: str):
    return (email, api_token)


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------

def fetch_github_data(token: str, repo: str) -> dict:
    """Fetch last 50 PRs (state=all) and compute metrics."""
    print(f"[GitHub] Fetching PRs for repo: {repo}")
    base_url = "https://api.github.com"
    headers = github_headers(token)

    prs_raw = []
    page = 1
    per_page = 50

    try:
        url = f"{base_url}/repos/{repo}/pulls"
        params = {"state": "all", "per_page": per_page, "page": page, "sort": "created", "direction": "desc"}
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        prs_raw = resp.json()
        print(f"[GitHub] Retrieved {len(prs_raw)} PRs from page {page}")
    except requests.HTTPError as exc:
        print(f"[GitHub] HTTP error fetching PRs: {exc}")
        return _empty_pr_data()
    except requests.RequestException as exc:
        print(f"[GitHub] Request error fetching PRs: {exc}")
        return _empty_pr_data()

    total = len(prs_raw)
    ai_assisted = 0
    security_flagged = 0
    recent_prs = []

    for pr in prs_raw:
        labels = [lbl.get("name", "") for lbl in pr.get("labels", [])]
        is_ai = "ai-assisted" in labels
        is_sec = "security-review-needed" in labels

        if is_ai:
            ai_assisted += 1
        if is_sec:
            security_flagged += 1

        if len(recent_prs) < 10:
            recent_prs.append({
                "number": pr.get("number"),
                "title": pr.get("title", ""),
                "author": (pr.get("user") or {}).get("login", ""),
                "state": pr.get("state", ""),
                "ai_assisted": is_ai,
                "security_review": is_sec,
                "created_at": pr.get("created_at", ""),
                "url": pr.get("html_url", ""),
            })

    ai_pct = round((ai_assisted / total) * 100) if total > 0 else 0

    print(f"[GitHub] Total: {total}, AI-assisted: {ai_assisted} ({ai_pct}%), Security-flagged: {security_flagged}")

    return {
        "total": total,
        "ai_assisted": ai_assisted,
        "ai_pct": ai_pct,
        "security_flagged": security_flagged,
        "recent": recent_prs,
    }


def _empty_pr_data() -> dict:
    return {
        "total": 0,
        "ai_assisted": 0,
        "ai_pct": 0,
        "security_flagged": 0,
        "recent": [],
    }


# ---------------------------------------------------------------------------
# Jira
# ---------------------------------------------------------------------------

def fetch_jira_data(base_url: str, email: str, api_token: str, board_id: str) -> dict | None:
    """Fetch active sprint data from Jira. Returns None if Jira not configured or on error."""
    print(f"[Jira] Fetching active sprint for board: {board_id}")
    auth = jira_auth(email, api_token)
    base_url = base_url.rstrip("/")

    # Step 1: get active sprint
    try:
        sprint_url = f"{base_url}/rest/agile/1.0/board/{board_id}/sprint"
        resp = requests.get(
            sprint_url,
            auth=auth,
            params={"state": "active"},
            timeout=30,
        )
        resp.raise_for_status()
        sprints = resp.json().get("values", [])
    except requests.HTTPError as exc:
        print(f"[Jira] HTTP error fetching sprint: {exc}")
        return None
    except requests.RequestException as exc:
        print(f"[Jira] Request error fetching sprint: {exc}")
        return None

    if not sprints:
        print("[Jira] No active sprint found.")
        return None

    sprint = sprints[0]
    sprint_id = sprint.get("id")
    sprint_name = sprint.get("name", "Unknown Sprint")
    sprint_start = sprint.get("startDate", "")
    sprint_end = sprint.get("endDate", "")
    print(f"[Jira] Active sprint: {sprint_name} (ID: {sprint_id})")

    # Step 2: get sprint issues
    try:
        issues_url = f"{base_url}/rest/agile/1.0/sprint/{sprint_id}/issue"
        all_issues = []
        start_at = 0
        max_results = 100

        while True:
            resp = requests.get(
                issues_url,
                auth=auth,
                params={"startAt": start_at, "maxResults": max_results},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            issues = data.get("issues", [])
            all_issues.extend(issues)
            total_fetched = data.get("total", 0)
            start_at += len(issues)
            if start_at >= total_fetched or not issues:
                break

        print(f"[Jira] Fetched {len(all_issues)} sprint issues")
    except requests.HTTPError as exc:
        print(f"[Jira] HTTP error fetching sprint issues: {exc}")
        return None
    except requests.RequestException as exc:
        print(f"[Jira] Request error fetching sprint issues: {exc}")
        return None

    committed_sp = 0.0
    done_sp = 0.0
    in_progress_count = 0
    total_issues = len(all_issues)

    for issue in all_issues:
        fields = issue.get("fields", {})
        story_points = fields.get("customfield_10016") or 0
        try:
            story_points = float(story_points)
        except (TypeError, ValueError):
            story_points = 0.0

        committed_sp += story_points
        status_name = (fields.get("status") or {}).get("name", "").lower()

        if status_name == "done":
            done_sp += story_points
        elif status_name in ("in progress", "in review", "in development"):
            in_progress_count += 1

    return {
        "name": sprint_name,
        "start": sprint_start,
        "end": sprint_end,
        "committed_sp": int(committed_sp),
        "done_sp": int(done_sp),
        "in_progress_count": in_progress_count,
        "total_issues": total_issues,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    github_token = get_env("GITHUB_TOKEN")
    github_repo = get_env("GITHUB_REPO")
    jira_base_url = get_env("JIRA_BASE_URL")
    jira_email = get_env("JIRA_EMAIL")
    jira_api_token = get_env("JIRA_API_TOKEN")
    jira_board_id = get_env("JIRA_BOARD_ID")
    output_path = get_env("OUTPUT_PATH", "portal-live/data/portal-data.json")

    github_configured = bool(github_token and github_repo)
    jira_configured = bool(jira_base_url and jira_email and jira_api_token and jira_board_id)

    print(f"[Config] GitHub configured: {github_configured}")
    print(f"[Config] Jira configured: {jira_configured}")
    print(f"[Config] Output path: {output_path}")

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # --- GitHub ---
    if github_configured:
        pr_data = fetch_github_data(github_token, github_repo)
    else:
        print("[GitHub] Not configured — using empty PR data.")
        pr_data = _empty_pr_data()

    # --- Jira ---
    sprint_data = None
    if jira_configured:
        sprint_data = fetch_jira_data(jira_base_url, jira_email, jira_api_token, jira_board_id)
    else:
        print("[Jira] Not configured — skipping sprint data.")

    # --- Assemble output ---
    output: dict = {
        "generated_at": generated_at,
        "source": {
            "github_repo": github_repo if github_repo else None,
            "jira_board": jira_board_id if jira_board_id else None,
            "jira_configured": jira_configured,
            "github_configured": github_configured,
        },
        "prs": pr_data,
        "adoption": {
            "ai_assisted_prs": pr_data["ai_assisted"],
            "total_prs": pr_data["total"],
            "ai_pct": pr_data["ai_pct"],
        },
    }

    if sprint_data is not None:
        output["sprint"] = sprint_data

    # --- Write output ---
    try:
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(output, fh, indent=2)
        print(f"[Output] Written to: {output_path}")
    except OSError as exc:
        print(f"[Output] ERROR writing file: {exc}")
        sys.exit(0)

    print("[Done] fetch_portal_data.py completed successfully.")


if __name__ == "__main__":
    main()
