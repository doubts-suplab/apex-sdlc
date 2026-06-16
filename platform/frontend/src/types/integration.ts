// mirrors backend schemas/integration.py
import { z } from "zod";

export const IntegrationTypeSchema = z.enum(["github", "jira", "rally", "confluence"]);
export type IntegrationType = z.infer<typeof IntegrationTypeSchema>;

export const IssueTrackerSchema = z.enum(["jira", "rally", "none"]);
export type IssueTracker = z.infer<typeof IssueTrackerSchema>;

export const LLMProviderSchema = z.enum(["anthropic", "ollama", "groq", "huggingface"]);
export type LLMProvider = z.infer<typeof LLMProviderSchema>;

export const IntegrationSchema = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  integration_type: IntegrationTypeSchema,
  config: z.record(z.unknown()),
  enabled: z.boolean(),
  last_synced_at: z.string().datetime().nullable(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});
export type Integration = z.infer<typeof IntegrationSchema>;

export const ProjectMetricsSchema = z
  .object({
    github: z
      .object({
        total_prs: z.number(),
        ai_assisted_prs: z.number(),
        ai_pct: z.number(),
        security_flagged: z.number(),
        open_prs: z.number(),
      })
      .optional(),
    jira: z
      .object({
        sprint_name: z.string(),
        committed_sp: z.number(),
        done_sp: z.number(),
        in_progress_count: z.number(),
      })
      .optional(),
    rally: z
      .object({
        iteration_name: z.string(),
        planned_velocity: z.number(),
        accepted_points: z.number(),
        in_progress_count: z.number(),
      })
      .optional(),
  })
  .nullable();
export type ProjectMetrics = z.infer<typeof ProjectMetricsSchema>;
