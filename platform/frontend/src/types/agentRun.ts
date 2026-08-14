import { z } from "zod";
import { PhaseTypeSchema } from "@/types/project";

// Mirrors the backend persistence read/write shapes:
// - app/api/v1/persistence.py (list_agent_runs / list_artifacts / gate_status / run-persist)
// - app/services/persistence_service.py (persist_phase return, gate_matrix)

export const AgentRunSchema = z.object({
  id: z.string(),
  phase: PhaseTypeSchema,
  agent_name: z.string(),
  action: z.string(),
  confidence: z.number(),
  auto_enforced: z.boolean(),
  outcome: z.string(),
  input_tokens: z.number(),
  output_tokens: z.number(),
  cost_usd: z.number(),
  duration_ms: z.number(),
  model: z.string(),
});
export type AgentRun = z.infer<typeof AgentRunSchema>;

export const AgentRunListSchema = z.object({
  total: z.number(),
  items: z.array(AgentRunSchema),
});

export const StoredArtifactSchema = z.object({
  id: z.string(),
  phase: PhaseTypeSchema,
  name: z.string(),
  kind: z.string(),
  version: z.number(),
  content_sha256: z.string(),
});
export type StoredArtifact = z.infer<typeof StoredArtifactSchema>;

export const StoredArtifactListSchema = z.object({
  total: z.number(),
  items: z.array(StoredArtifactSchema),
});

export const GateStatusSchema = z.object({
  phase: PhaseTypeSchema,
  status: z.string(),
});
export type GateStatus = z.infer<typeof GateStatusSchema>;

export const GateStatusListSchema = z.object({
  gates: z.array(GateStatusSchema),
});

// POST /projects/{id}/phases/{phase}/agents/run-persist → PersistenceService.persist_phase(...)
export const RunPersistResultSchema = z.object({
  project_id: z.string(),
  phase: PhaseTypeSchema,
  agent: z.string(),
  action: z.string(),
  confidence: z.number(),
  auto_enforced: z.boolean(),
  outcome: z.string(),
  artifacts: z.number(),
  new_versions: z.number(),
  pii_events: z.number(),
});
export type RunPersistResult = z.infer<typeof RunPersistResultSchema>;

// GET /projects/{id}/artifacts/{artifact_id} — the stored artifact with its content.
export const ArtifactContentSchema = z.object({
  id: z.string(),
  phase: PhaseTypeSchema,
  name: z.string(),
  title: z.string(),
  kind: z.string(),
  version: z.number(),
  content_sha256: z.string(),
  content: z.string(),
});
export type ArtifactContent = z.infer<typeof ArtifactContentSchema>;

// GET /projects/{id}/approvals — durable gate approvals (history + current).
export const ApprovalItemSchema = z.object({
  id: z.string(),
  phase: PhaseTypeSchema,
  decision: z.string(),
  approver_subject: z.string(),
  approver_persona: z.string(),
  member_bound: z.boolean(),
  note: z.string().nullable(),
  created_at: z.string().nullable(),
});
export const ApprovalsListSchema = z.object({
  total: z.number(),
  approved_phases: z.array(PhaseTypeSchema),
  items: z.array(ApprovalItemSchema),
});

// POST /projects/{id}/phases/{phase}/approve
export const ApprovalResultSchema = z.object({
  id: z.string(),
  phase: PhaseTypeSchema,
  decision: z.string(),
  member_bound: z.boolean(),
});
export type ApprovalResult = z.infer<typeof ApprovalResultSchema>;
