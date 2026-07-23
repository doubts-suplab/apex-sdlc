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
