import { z } from "zod";
import { PhaseTypeSchema } from "@/types/project";

// Mirrors app/api/v1/persistence.py governance read endpoints (CISO/Lead-gated) and
// app/models/audit.py (AuditLog / PiiEvent / PolicyViolation).

export const AuditLogEntrySchema = z.object({
  id: z.string(),
  actor: z.string(),
  phase: PhaseTypeSchema,
  agent_name: z.string(),
  action: z.string(),
  model: z.string(),
  input_tokens: z.number(),
  output_tokens: z.number(),
  cost_usd: z.number(),
  auto_enforced: z.boolean(),
  summary: z.string(),
});
export type AuditLogEntry = z.infer<typeof AuditLogEntrySchema>;

export const AuditLogListSchema = z.object({
  total: z.number(),
  items: z.array(AuditLogEntrySchema),
});

export const PiiEventSchema = z.object({
  id: z.string(),
  phase: PhaseTypeSchema,
  label: z.string(),
  direction: z.string(),
  action: z.string(),
  occurrences: z.number(),
});
export type PiiEvent = z.infer<typeof PiiEventSchema>;

export const PiiEventListSchema = z.object({
  total: z.number(),
  items: z.array(PiiEventSchema),
});

export const PolicyViolationSchema = z.object({
  id: z.string(),
  phase: PhaseTypeSchema,
  policy: z.string(),
  severity: z.string(),
  detail: z.string(),
  status: z.string(),
});
export type PolicyViolation = z.infer<typeof PolicyViolationSchema>;

export const PolicyViolationListSchema = z.object({
  total: z.number(),
  items: z.array(PolicyViolationSchema),
});
