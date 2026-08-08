import { z } from "zod";
// mirrors backend app/agents/orchestrator.py (JourneyResult / JourneyPhase) and app/api/v1/journey.py

export const JourneyArtifactSchema = z.object({
  name: z.string(),
  title: z.string(),
  kind: z.string(),
  format: z.string(),
  content: z.string(),
});
export type JourneyArtifact = z.infer<typeof JourneyArtifactSchema>;

export const JourneyPhaseSchema = z.object({
  phase: z.string(),
  label: z.string(),
  persona: z.string(),
  stakeholders: z.array(z.string()),
  agent_name: z.string(),
  authority: z.string(),
  action: z.string(),
  confidence: z.number(),
  // The confidence bar this phase had to clear to auto-enforce; null ⇒ never auto-enforces (gate rule G-5).
  confidence_threshold: z.number().nullable().optional(),
  auto_enforced: z.boolean(),
  outcome: z.string(), // "auto-enforced" | "human-review"
  rationale: z.string(),
  eeik_agent: z.string(),
  summary: z.string(),
  artifacts: z.array(JourneyArtifactSchema),
});
export type JourneyPhase = z.infer<typeof JourneyPhaseSchema>;

export const JourneyStatsSchema = z.object({
  phase_count: z.number(),
  auto_enforced_count: z.number(),
  human_review_count: z.number(),
  artifact_count: z.number(),
  audit_entries: z.number(),
  confidence_gate_bypass_total: z.number(),
});
export type JourneyStats = z.infer<typeof JourneyStatsSchema>;

export const JourneyProjectSchema = z.object({
  name: z.string(),
  slug: z.string(),
  description: z.string().optional(),
  stack: z.string().optional(),
  feature_name: z.string().optional(),
  version: z.string().optional(),
});
export type JourneyProject = z.infer<typeof JourneyProjectSchema>;

export const JourneySchema = z.object({
  project: JourneyProjectSchema,
  phases: z.array(JourneyPhaseSchema),
  stats: JourneyStatsSchema,
  persona: z.string().optional(),
});
export type Journey = z.infer<typeof JourneySchema>;

// mirrors backend app/gates/engine.py (GateResult) + app/api/v1/journey.py reference-gates response
export const GateCheckSchema = z.object({
  name: z.string(),
  passed: z.boolean(),
  detail: z.string(),
});

export const GateResultSchema = z.object({
  phase: z.string(),
  status: z.enum(["passed", "pending", "failed"]),
  checks: z.array(GateCheckSchema),
  reason: z.string(),
});
export type GateResult = z.infer<typeof GateResultSchema>;

export const ReferenceGatesSchema = z.object({
  approved: z.array(z.string()),
  gates: z.array(GateResultSchema),
  blocking_phase: z.string().nullable(),
  all_passed: z.boolean(),
});
export type ReferenceGates = z.infer<typeof ReferenceGatesSchema>;

// mirrors backend app/agents/authority.py (authority_model) + app/api/v1/journey.py /journey/authority
export const AuthorityPhaseSchema = z.object({
  phase: z.string(),
  label: z.string(),
  authority: z.string(),
  auto_enforces: z.boolean(),
  confidence_threshold: z.number().nullable(),
  note: z.string(),
});
export type AuthorityPhase = z.infer<typeof AuthorityPhaseSchema>;

export const AuthorityModelSchema = z.object({
  gate_rule: z.string(),
  authority_ladder: z.array(z.string()),
  phases: z.array(AuthorityPhaseSchema),
});
export type AuthorityModel = z.infer<typeof AuthorityModelSchema>;
