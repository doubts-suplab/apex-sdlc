# APEX Jira Bridge

AWS Lambda that receives **Jira webhooks**, enriches them with **Claude AI**, and writes AI summaries to **Confluence**.

## What it does

| Webhook Event | Action |
|---|---|
| `jira:issue_created` | Generates a stakeholder brief + AC hints → new Confluence page |
| `jira:issue_updated` (status change) | Appends an AI change note to the existing brief |
| `sprint_started` | Creates a sprint kickoff digest (theme, risk, recommendation) |
| `sprint_closed` | Creates a sprint close summary (velocity, carry-forward analysis) |

## Architecture

```
Jira → API Gateway → Lambda (handler.py)
                         ↓
                  AWS Secrets Manager
                  (ANTHROPIC_API_KEY, Confluence creds)
                         ↓
                  Claude API (claude-haiku)
                         ↓
                  Confluence REST API
```

## Setup

### 1. Create the Secrets Manager secret

```bash
aws secretsmanager create-secret \
  --name apex/jira-bridge \
  --secret-string '{
    "ANTHROPIC_API_KEY": "sk-ant-...",
    "CONFLUENCE_EMAIL": "you@company.com",
    "CONFLUENCE_API_TOKEN": "..."
  }'
```

### 2. Environment variables (Lambda config)

```
APEX_SECRET_NAME      = apex/jira-bridge
CONFLUENCE_BASE_URL   = https://your-org.atlassian.net/wiki
CONFLUENCE_SPACE_KEY  = APEX
CLAUDE_MODEL          = claude-haiku-4-5-20251001
PII_GUARD_ENABLED     = true
```

### 3. Deploy

```bash
pip install -r requirements.txt -t ./package/
cd package && zip -r ../function.zip . && cd ..
zip function.zip handler.py confluence_writer.py pii_guard.py

aws lambda create-function \
  --function-name apex-jira-bridge \
  --runtime python3.12 \
  --handler handler.lambda_handler \
  --zip-file fileb://function.zip \
  --role arn:aws:iam::ACCOUNT:role/apex-lambda-role \
  --timeout 30 \
  --memory-size 256
```

### 4. Configure Jira webhook

In Jira → System → WebHooks, add:
- URL: `https://API_GW_ID.execute-api.REGION.amazonaws.com/prod/jira`
- Events: Issue Created, Issue Updated, Sprint Started, Sprint Closed

## IAM permissions required

```json
{
  "Effect": "Allow",
  "Action": [
    "secretsmanager:GetSecretValue",
    "comprehend:DetectPiiEntities",
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ],
  "Resource": "*"
}
```

## PII Guard

When `PII_GUARD_ENABLED=true`, issue descriptions are scrubbed for PII (names, emails, phone numbers, national IDs) via AWS Comprehend before being sent to the Claude API. Scrubbed tokens are replaced with `[REDACTED]`.

See `../pii-guard/` for the shared guard module.
