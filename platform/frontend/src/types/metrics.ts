import { z } from "zod";
// mirrors backend app/agents/metrics.py (metrics_by_persona) and app/api/v1/journey.py::get_reference_metrics

export const PersonaMetricsSchema = z.object({
  persona: z.string(),
  runs: z.number(),
  input_tokens: z.number(),
  output_tokens: z.number(),
  cost_usd: z.number(),
  duration_ms: z.number(),
  avg_latency_ms: z.number(),
});
export type PersonaMetrics = z.infer<typeof PersonaMetricsSchema>;

export const MetricsTotalsSchema = z.object({
  runs: z.number(),
  input_tokens: z.number(),
  output_tokens: z.number(),
  cost_usd: z.number(),
  duration_ms: z.number(),
});
export type MetricsTotals = z.infer<typeof MetricsTotalsSchema>;

export const ReferenceMetricsSchema = z.object({
  project: z.record(z.string(), z.unknown()),
  personas: z.array(PersonaMetricsSchema),
  totals: MetricsTotalsSchema,
  pricing_model: z.string(),
});
export type ReferenceMetrics = z.infer<typeof ReferenceMetricsSchema>;
