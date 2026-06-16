# APEX SDLC Platform

This directory contains the full APEX platform — the enterprise AI-powered SDLC operating system. It supersedes the legacy `portal/` and `portal-live/` prototypes.

## What is in here

```
platform/
  backend/          FastAPI application (Python 3.12)
  frontend/         Next.js 14 application (TypeScript strict)
  docker-compose.yml  Local development environment
  project-manifest.yaml  eeik-bootstrap manifest for this project
  CLAUDE.md         Master CLAUDE.md — read this before touching anything
  README.md         This file
```

## Running locally

Prerequisites: Docker Desktop (or Docker Engine + Compose plugin), an Anthropic API key.

```bash
cd platform

# Copy environment template and fill in your keys
cp .env.example .env
# Set ANTHROPIC_API_KEY, GITHUB_TOKEN, JIRA_* and CONFLUENCE_* values

# Start all services
docker compose up --build

# Services come up at:
#   Frontend:  http://localhost:3000
#   Backend:   http://localhost:8000
#   API docs:  http://localhost:8000/docs
#   Postgres:  localhost:5432  (apex / apex_dev / apex_platform)
#   Redis:     localhost:6379
```

To run only the backend stack (no frontend build):

```bash
docker compose up postgres redis backend
```

## eeik-bootstrap usage

This project is scaffolded and extended using [eeik-bootstrap](https://github.com/your-org/eeik-bootstrap). The `project-manifest.yaml` in this directory drives code generation.

Key commands (run from repo root with eeik CLI installed):

```bash
# Regenerate scaffold from manifest (non-destructive — skips existing files)
eeik generate-repo --manifest platform/project-manifest.yaml --target platform/

# Run a specific agent against the backend
eeik agent python-developer "implement the artifact versioning service"

# Run the DBA advisor on schema changes
eeik agent dba-advisor "review alembic migration 0003_add_artifact_versions"
```

Capability packs active for this project: `core`, `python`, `react`, `aws`, `ai-engineering`, `governance`, `delivery`, `containers`.

Standards files that govern all generated code: `fastapi.md`, `python.md`, `react-standard.md`, `aws.md`, `sql.md`, `testing.md`, `api-standard.md`, `security-baseline.md`, `ai-governance.md`.
