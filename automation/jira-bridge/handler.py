"""
APEX Jira Bridge — AWS Lambda Handler
Receives Jira webhook events, calls Claude API to generate AI summaries,
and writes enriched content back to Confluence via the Confluence Writer.

Trigger: Jira webhook (issue:created, issue:updated, sprint:started, sprint:closed)
IAM: Needs secretsmanager:GetSecretValue, comprehend:DetectPiiEntities

Environment Variables:
  APEX_SECRET_NAME   — AWS Secrets Manager secret containing API keys
  CONFLUENCE_BASE_URL — e.g. https://your-org.atlassian.net/wiki
  CONFLUENCE_SPACE_KEY — e.g. APEX
  CLAUDE_MODEL       — default: claude-haiku-4-5-20251001
  PII_GUARD_ENABLED  — true/false (default: true)
"""

import json
import logging
import os
import boto3
from typing import Any

import anthropic

from confluence_writer import ConfluenceWriter
from pii_guard import PIIGuard

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Secrets bootstrap (cached across warm invocations)
# ---------------------------------------------------------------------------

_secrets: dict[str, str] | None = None


def _load_secrets() -> dict[str, str]:
    global _secrets
    if _secrets is not None:
        return _secrets

    secret_name = os.environ["APEX_SECRET_NAME"]
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_name)
    _secrets = json.loads(response["SecretString"])
    return _secrets


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Route Jira webhook events to the appropriate handler."""
    logger.info("Received event: %s", json.dumps(event, default=str))

    secrets = _load_secrets()
    claude_client = anthropic.Anthropic(api_key=secrets["ANTHROPIC_API_KEY"])
    confluence = ConfluenceWriter(
        base_url=os.environ["CONFLUENCE_BASE_URL"],
        space_key=os.environ.get("CONFLUENCE_SPACE_KEY", "APEX"),
        username=secrets["CONFLUENCE_EMAIL"],
        api_token=secrets["CONFLUENCE_API_TOKEN"],
    )
    pii_guard = PIIGuard(enabled=os.environ.get("PII_GUARD_ENABLED", "true").lower() == "true")

    webhook_event = event.get("webhookEvent", "")

    handlers = {
        "jira:issue_created": _handle_issue_created,
        "jira:issue_updated": _handle_issue_updated,
        "sprint_started": _handle_sprint_started,
        "sprint_closed": _handle_sprint_closed,
    }

    handler_fn = handlers.get(webhook_event)
    if handler_fn is None:
        logger.warning("Unhandled webhook event: %s", webhook_event)
        return {"statusCode": 200, "body": "Event not handled"}

    try:
        handler_fn(event, claude_client, confluence, pii_guard, secrets)
        return {"statusCode": 200, "body": "OK"}
    except Exception as exc:
        logger.error("Handler failed: %s", exc, exc_info=True)
        return {"statusCode": 500, "body": str(exc)}


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------


def _handle_issue_created(
    event: dict,
    claude: anthropic.Anthropic,
    confluence: "ConfluenceWriter",
    pii_guard: "PIIGuard",
    secrets: dict,
) -> None:
    """When a new story/bug/task is created, generate an AI-enriched brief."""
    issue = event["issue"]
    key = issue["key"]
    summary = issue["fields"]["summary"]
    description = issue["fields"].get("description") or ""
    issue_type = issue["fields"]["issuetype"]["name"]
    priority = issue["fields"].get("priority", {}).get("name", "Medium")

    # PII scrub before sending to external API
    safe_description = pii_guard.scrub(description)

    prompt = f"""You are an APEX Business Analyst assistant.

A new Jira {issue_type} has been created:
- Key: {key}
- Summary: {summary}
- Priority: {priority}
- Description: {safe_description}

Generate:
1. A one-paragraph plain-English brief suitable for a stakeholder (no Jira jargon)
2. Three bullet points: acceptance criteria hints the BA should validate
3. Any obvious risks or dependencies to flag NOW (max 2 sentences)

Be concise. Avoid repeating the summary verbatim."""

    response = claude.messages.create(
        model=os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    ai_brief = response.content[0].text

    confluence.create_or_update_page(
        title=f"[APEX AI Brief] {key} — {summary}",
        body=_wrap_html(key, summary, ai_brief, "Issue Created"),
        parent_title="APEX AI Briefs",
    )
    logger.info("Created Confluence brief for %s", key)


def _handle_issue_updated(
    event: dict,
    claude: anthropic.Anthropic,
    confluence: "ConfluenceWriter",
    pii_guard: "PIIGuard",
    secrets: dict,
) -> None:
    """When an issue transitions status, append an AI change note."""
    issue = event["issue"]
    key = issue["key"]
    changelog = event.get("changelog", {})

    # Only act on status transitions
    status_changes = [
        item for item in changelog.get("items", []) if item["field"] == "status"
    ]
    if not status_changes:
        return

    from_status = status_changes[0]["fromString"]
    to_status = status_changes[0]["toString"]
    summary = issue["fields"]["summary"]

    prompt = f"""Jira issue {key} ("{summary}") moved from "{from_status}" → "{to_status}".

Write a one-sentence change note for the Confluence audit trail.
Flag if this transition is unusual (e.g. moving backward in the workflow) and suggest a follow-up action."""

    response = claude.messages.create(
        model=os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    note = response.content[0].text

    confluence.append_to_page(
        title=f"[APEX AI Brief] {key} — {summary}",
        content=_status_change_html(key, from_status, to_status, note),
    )
    logger.info("Appended status change note for %s", key)


def _handle_sprint_started(
    event: dict,
    claude: anthropic.Anthropic,
    confluence: "ConfluenceWriter",
    pii_guard: "PIIGuard",
    secrets: dict,
) -> None:
    """On sprint start, generate an AI sprint kickoff digest."""
    sprint = event.get("sprint", {})
    sprint_name = sprint.get("name", "Unknown Sprint")
    sprint_goal = sprint.get("goal", "No goal set")
    issues = event.get("issues", [])

    story_list = "\n".join(
        f"- [{i['key']}] {i['fields']['summary']} ({i['fields']['issuetype']['name']}, {i['fields'].get('story_points', '?')} SP)"
        for i in issues[:30]  # cap at 30 to avoid huge prompts
    )

    prompt = f"""Sprint "{sprint_name}" has just started.
Sprint goal: {sprint_goal}

Committed stories:
{story_list}

Write a sprint kickoff digest for the PM / Agile coach (3–4 sentences):
1. Summarise the sprint theme in plain English
2. Call out the highest-risk story and why
3. Suggest one process improvement based on the story mix (e.g. many bugs → regression focus)"""

    response = claude.messages.create(
        model=os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    digest = response.content[0].text

    confluence.create_or_update_page(
        title=f"[APEX] {sprint_name} — Kickoff Digest",
        body=_wrap_html("SPRINT", sprint_name, digest, "Sprint Kickoff"),
        parent_title="APEX Sprint Digests",
    )
    logger.info("Created sprint kickoff digest for %s", sprint_name)


def _handle_sprint_closed(
    event: dict,
    claude: anthropic.Anthropic,
    confluence: "ConfluenceWriter",
    pii_guard: "PIIGuard",
    secrets: dict,
) -> None:
    """On sprint close, generate velocity summary and carry-forward analysis."""
    sprint = event.get("sprint", {})
    sprint_name = sprint.get("name", "Unknown Sprint")
    completed = event.get("completedIssues", [])
    incomplete = event.get("incompleteIssues", [])
    velocity_committed = event.get("velocityStats", {}).get("estimated", {}).get("value", 0)
    velocity_completed = event.get("velocityStats", {}).get("completed", {}).get("value", 0)

    carry_list = "\n".join(f"- [{i['key']}] {i['fields']['summary']}" for i in incomplete[:10])

    prompt = f"""Sprint "{sprint_name}" has just closed.
- Committed: {velocity_committed} SP
- Completed: {velocity_completed} SP ({round(velocity_completed / max(velocity_committed, 1) * 100)}% velocity)
- Carry-forward stories ({len(incomplete)}):
{carry_list if carry_list else "  None"}

Write an executive sprint close summary (4–5 sentences):
1. Velocity assessment (on track / below / above target)
2. Pattern behind any carry-forward (if present)
3. One actionable recommendation for next sprint planning"""

    response = claude.messages.create(
        model=os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    summary = response.content[0].text

    confluence.create_or_update_page(
        title=f"[APEX] {sprint_name} — Close Summary",
        body=_wrap_html("SPRINT", sprint_name, summary, "Sprint Close"),
        parent_title="APEX Sprint Digests",
    )
    logger.info("Created sprint close summary for %s", sprint_name)


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------


def _wrap_html(key: str, title: str, content: str, event_type: str) -> str:
    return f"""<h2>APEX AI Brief — {event_type}</h2>
<p><strong>Reference:</strong> {key} | <strong>Title:</strong> {title}</p>
<hr/>
<p>{content.replace(chr(10), '<br/>')}</p>
<p><em>Generated by APEX Jira Bridge · Model: {os.environ.get('CLAUDE_MODEL', 'claude-haiku-4-5-20251001')}</em></p>"""


def _status_change_html(key: str, from_s: str, to_s: str, note: str) -> str:
    return f"""<h3>Status Transition: {from_s} → {to_s}</h3>
<p>{note}</p>
<p><em>APEX AI note</em></p>"""
