# APEX Platform — Frontend (Next.js 14)

## Stack

| Component | Choice |
|-----------|--------|
| Framework | Next.js 14 App Router |
| Language | TypeScript 5.x strict mode (`"strict": true` in tsconfig) |
| Data fetching | TanStack Query v5 |
| Styling | Tailwind CSS |
| Components | shadcn/ui |
| Forms | React Hook Form + Zod |
| HTTP client | native `fetch` wrapped in `lib/api.ts` |
| Icons | lucide-react |
| Markdown render | react-markdown + remark-gfm |
| Diagrams | mermaid.js (dynamic import, SSR disabled) |
| Testing | Jest + Testing Library React (unit), Playwright (e2e) |

## Directory Layout

```
frontend/
  src/
    app/                                  Next.js App Router root
      layout.tsx                          Root layout: fonts, global providers (QueryClient, ThemeProvider)
      page.tsx                            Org home — project registry grid, KPI summary
      (projects)/
        layout.tsx                        Projects shell layout (persistent sidebar)
        projects/
          page.tsx                        Project list with search/filter
          new/
            page.tsx                      Onboard new project wizard (multi-step form)
          [projectId]/
            layout.tsx                    Project shell: project nav, PersonaSwitcher
            page.tsx                      Project detail — SDLC timeline + live metrics
            phase/
              [phase]/
                page.tsx                  Phase detail — artifact gallery + Run Agent
            generate/
              page.tsx                    Artifact generator: select phase, configure inputs, run
      governance/
        layout.tsx
        page.tsx                          Org governance: audit log, violations, gate matrix, PII events
      settings/
        page.tsx                          Org settings: integration configs, team management
    components/
      ui/                                 shadcn/ui generated primitives — do NOT manually edit
      layout/
        TopNav.tsx                        Logo, org switcher, user avatar menu
        Sidebar.tsx                       Collapsible project nav with active state
        PersonaSwitcher.tsx               Role selector dropdown — "use client"; persisted to localStorage
      projects/
        ProjectCard.tsx                   Summary card: name, phase badge, sprint progress, last run
        ProjectGrid.tsx                   Responsive grid of ProjectCards with search/filter bar
        OnboardProjectForm.tsx            Multi-step wizard: name → GitHub → Jira → Confluence → team
        SDLCTimeline.tsx                  Horizontal 7-phase timeline with gate pass/fail indicators
        LiveMetricsBar.tsx                Open PRs, sprint velocity, coverage %, last deploy time
      phases/
        PhasePanel.tsx                    Active phase: artifact list + Run Agent button
        ArtifactCard.tsx                  Single artifact: title, type, created, version badge, actions
        ArtifactGallery.tsx               Grid/list toggle of ArtifactCards
        ArtifactViewer.tsx                Markdown renderer + Mermaid diagram support (client-side only)
        ArtifactVersionHistory.tsx        Chronological version list with diff link
        RunAgentButton.tsx                Triggers POST to /agents/run; opens AgentProgressDrawer
      agents/
        AgentProgressDrawer.tsx           shadcn Sheet slide-over with SSE streaming output — "use client"
        AgentRunList.tsx                  History of previous agent runs for a phase
        AgentRunDetail.tsx                Full run: message turns, token count, cost USD, duration
      governance/
        AuditLogTable.tsx                 Filterable audit log with expandable row detail
        ViolationsPanel.tsx               Policy violations with severity badge + remediation status
        GateStatusGrid.tsx                Projects × phases matrix — pass/fail cells
        PIIEventLog.tsx                   PII detection events: pattern, field, action taken
    lib/
      api.ts                              Base fetch wrapper: adds auth header, base URL, error handling
      queries/
        projects.ts                       useProjects, useProject, useCreateProject, useUpdateProject
        phases.ts                         usePhases, usePhase, useGateStatus, useEvaluateGate
        artifacts.ts                      useArtifacts, useArtifact, useArtifactVersions, useDownloadUrl
        agents.ts                         useAgentRuns, useAgentRun, useRunAgent (mutation)
        governance.ts                     useAuditLog, useViolations, usePIIEvents, useGateMatrix
      sse.ts                              useAgentStream(runId): EventSource hook → AgentProgress[]
      persona.ts                          usePersona(): get/set persona; localStorage persistence
      formatters.ts                       formatDate, formatTokenCount, formatCostUsd, formatDuration
    types/
      project.ts                          Project, Organisation, ProjectIntegration interfaces
      phase.ts                            Phase, PhaseGate, GateEvaluationResult interfaces
      artifact.ts                         Artifact, ArtifactVersion, ArtifactType interfaces
      agent.ts                            AgentRun, AgentRunMessage, AgentProgress interfaces
      governance.ts                       AuditLog, PIIEvent, PolicyViolation interfaces
      common.ts                           PaginatedResponse<T>, ApiError, Persona enum, UUID type
  public/
  Dockerfile
  next.config.ts
  tailwind.config.ts
  tsconfig.json                           "strict": true required
  package.json
```

## Persona Switcher

The persona switcher is a top-level concept. It persists the active persona to `localStorage` and filters which nav items and KPI cards are visible per persona.

```typescript
// lib/persona.ts
export type Persona = 'developer' | 'ba' | 'qa' | 'pm' | 'lead' | 'architect' | 'ciso';

export function usePersona() {
  const [persona, setPersona] = useState<Persona>(() => {
    if (typeof window === 'undefined') return 'developer';
    return (localStorage.getItem('apex_persona') as Persona) ?? 'developer';
  });
  const switchPersona = (p: Persona) => {
    localStorage.setItem('apex_persona', p);
    setPersona(p);
  };
  return { persona, switchPersona };
}
```

Persona visibility rules (which sections each persona sees by default):

| Persona | Nav items shown |
|---------|----------------|
| developer | Projects, Phases (Development), Artifacts |
| ba | Projects, Phases (Requirements), Artifact generator |
| qa | Projects, Phases (Testing), Artifacts |
| pm | Projects, SDLC Timeline, Metrics |
| lead | All sections |
| architect | Projects, Phases (Architecture), Governance |
| ciso | Governance only (audit log, PII events, violations) |

## Real-Time Agent Progress (SSE)

Agent runs are long-lived (30s–5min). The backend streams progress via Server-Sent Events.

```typescript
// lib/sse.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export function useAgentStream(runId: string | null) {
  const [messages, setMessages] = useState<AgentProgress[]>([]);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!runId) return;
    const es = new EventSource(`${API_BASE}/api/v1/agents/${runId}/stream`);
    es.onmessage = (e) => {
      const msg: AgentProgress = JSON.parse(e.data);
      if (msg.type === 'done') { setDone(true); es.close(); return; }
      setMessages(prev => [...prev, msg]);
    };
    es.onerror = () => es.close();
    return () => es.close();
  }, [runId]);

  return { messages, done };
}
```

`AgentProgressDrawer` uses this hook and renders streamed text chunks inside a scrollable `<pre>` block. Mermaid diagrams in the output are detected by ` ```mermaid ` fences and rendered client-side.

## API Client Pattern

```typescript
// lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  constructor(public readonly problem: { status: number; title: string; detail: string }) {
    super(problem.detail);
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}/api/v1${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const problem = await res.json();
    throw new ApiError(problem);
  }
  return res.json() as Promise<T>;
}
```

## TanStack Query Hook Pattern

```typescript
// lib/queries/projects.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import type { Project, PaginatedResponse } from '@/types';

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: () => apiFetch<PaginatedResponse<Project>>('/projects'),
    staleTime: 30_000,
  });
}

export function useProject(projectId: string) {
  return useQuery({
    queryKey: ['projects', projectId],
    queryFn: () => apiFetch<Project>(`/projects/${projectId}`),
    staleTime: 30_000,
    enabled: !!projectId,
  });
}

export function useRunAgent(projectId: string, phase: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (inputs: Record<string, unknown>) =>
      apiFetch<{ run_id: string }>(`/projects/${projectId}/phases/${phase}/agents/run`, {
        method: 'POST',
        body: JSON.stringify({ inputs }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agents', projectId, phase] });
    },
  });
}
```

## Key Pages

### Org Home (`/`)

- Hero strip: org name, total projects count, AI agent runs this month, cost MTD
- ProjectGrid: filtered by persona. Developers see only their assigned projects.
- "Onboard Project" button → multi-step wizard (OnboardProjectForm)
- Filter bar: by current phase, by tech type (spring-boot / angular / mainframe / python / fastapi)

### Project Detail (`/projects/[projectId]`)

- Header: project name, type badge, links to GitHub repo and Jira board
- PersonaSwitcher (top-right) — changes KPI cards shown below
- SDLCTimeline — horizontal bar: 7 phases; current phase highlighted; gate status (pass = green, fail = red, pending = grey); click phase to navigate to `/phase/[phase]`
- LiveMetricsBar — open PR count (GitHub live), sprint story points done/total (Jira live), test coverage % (last CI run), last deployment timestamp
- PhasePanel for active phase below timeline: artifact count, last agent run, Run Agent button

### Phase Detail (`/projects/[projectId]/phase/[phase]`)

- Phase header: phase name, status badge (active/completed/blocked), started date
- "Run Agent" button → POST to backend → opens AgentProgressDrawer with SSE streaming
- ArtifactGallery: all artifacts for this phase; each card shows title, type, version, created date, "View" + "Publish to Confluence" + "Download" actions
- AgentRunList: table of previous runs for this phase with status, model, tokens, cost, duration

### Governance (`/governance`)

- Visible to `lead`, `architect`, `ciso` personas only
- GateStatusGrid: matrix — all projects (rows) × all phases (columns) → coloured pass/fail cells
- AuditLogTable: filterable by project, actor, model, phase, date range; expandable rows show before/after artifact state
- ViolationsPanel: open policy violations grouped by severity (critical/high/medium); each row shows policy, project, phase, detected date, remediation status
- PIIEventLog: PII detection events; shows which field, which pattern, whether redacted or blocked

## Environment Variables

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=APEX SDLC Platform
```

No other env vars should be accessed in frontend code. All sensitive config lives in the backend.

## Non-Negotiables

- **App Router only** — no `pages/` directory, no `getServerSideProps`, no `getStaticProps`
- **Server components by default** — add `"use client"` only for: event handlers, hooks (`useState`, `useEffect`), browser APIs (`localStorage`, `EventSource`)
- **No `any` types** — strict TypeScript; use `unknown` + type guards when input type is genuinely unknown
- **TanStack Query for all API state** — no raw `useEffect(() => { fetch(...) }, [])` patterns
- **Zod schemas must mirror backend Pydantic models** — when backend schema changes, update corresponding Zod schema in `types/`; add a comment `// mirrors backend schemas/{file}.py`
- **Mermaid client-side only** — always: `const Mermaid = dynamic(() => import('./MermaidRenderer'), { ssr: false })`
- **No inline styles** — Tailwind utility classes only; no `style={{...}}` props
- **shadcn/ui for primitives** — Button, Card, Dialog, Table, Badge, Sheet, Tabs, Drawer; never add a second component library

## Component Guidelines

- `AgentProgressDrawer` — uses shadcn `Sheet` (side panel). State: `open`, `runId`. Mounts SSE hook when `runId` is set.
- `ArtifactViewer` — renders Markdown via `react-markdown` + `remark-gfm`. Detects ` ```mermaid ` fences, replaces with dynamically imported Mermaid renderer.
- `SDLCTimeline` — pure presentational; receives phase array with status; emits `onPhaseClick` callback.
- `PersonaSwitcher` — must be `"use client"` (uses `localStorage`). Renders as a shadcn `Select` dropdown in `TopNav`.
- Data tables (`AuditLogTable`, `ViolationsPanel`) — use shadcn DataTable pattern with `@tanstack/react-table` column definitions.
- `OnboardProjectForm` — multi-step using React Hook Form + Zod. Each step validated before advancing.

## eeik Agents for This Directory

| Task | eeik Command |
|------|-------------|
| Implement a new page | "Using react-developer agent, implement the phase detail page at `app/projects/[projectId]/phase/[phase]/page.tsx` per the CLAUDE.md layout spec" |
| Create a component | "Using react-developer agent, create `SDLCTimeline.tsx` with 7 phases, gate status colours, and click navigation" |
| Add TanStack Query hook | "Using react-developer agent, create query hooks for artifacts in `lib/queries/artifacts.ts` matching the backend artifact router" |
| Fix TypeScript strict errors | "Using react-developer agent, fix all TypeScript errors in `lib/queries/` — no `any` types allowed" |
| Add Playwright e2e test | "Using react-developer agent, write Playwright test for the onboard project multi-step wizard flow" |
| Review before PR | `/review` |
