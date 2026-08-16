import { z } from "zod";

// mirrors backend schemas/delivery.py + schemas/portfolio.py

export const DeliveryStatusSchema = z.enum([
  "proposed",
  "planned",
  "in_progress",
  "done",
  "dropped",
]);
export type DeliveryStatus = z.infer<typeof DeliveryStatusSchema>;

export const DeliveryPrioritySchema = z.enum(["low", "medium", "high", "critical"]);
export type DeliveryPriority = z.infer<typeof DeliveryPrioritySchema>;

export const DeliverySourceSchema = z.enum(["human", "agent"]);
export type DeliverySource = z.infer<typeof DeliverySourceSchema>;

export const DeliverySchema = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  title: z.string(),
  description: z.string().nullable(),
  status: DeliveryStatusSchema,
  priority: DeliveryPrioritySchema,
  estimate_points: z.number().int().nullable(),
  target_ref: z.string().nullable(),
  source: DeliverySourceSchema,
  created_at: z.string(),
  updated_at: z.string(),
});
export type Delivery = z.infer<typeof DeliverySchema>;

export const DeliveryPublishResponseSchema = z.object({
  delivery: DeliverySchema,
  issue_url: z.string(),
  issue_number: z.number().int().nullable(),
});
export type DeliveryPublishResponse = z.infer<typeof DeliveryPublishResponseSchema>;

// mirrors backend schemas/portfolio.py (PortfolioProjectRow)
export const PortfolioProjectRowSchema = z.object({
  project_id: z.string().uuid(),
  name: z.string(),
  slug: z.string(),
  github_repo: z.string().nullable(),
  delivery_count: z.number().int(),
  estimate_points: z.number().int(),
  open_count: z.number().int(),
  // Governed posture from the project's ingested eeik manifest (null when none ingested).
  domain: z.string().nullable().default(null),
  governance_profile: z.string().nullable().default(null),
  compliance_frameworks: z.array(z.string()).default([]),
  coverage_threshold: z.number().int().nullable().default(null),
  resolved_pack_count: z.number().int().nullable().default(null),
  manifest_engine: z.string().nullable().default(null),
});
export type PortfolioProjectRow = z.infer<typeof PortfolioProjectRowSchema>;

export const PortfolioSummarySchema = z.object({
  organisation_id: z.string().uuid(),
  project_count: z.number().int(),
  delivery_count: z.number().int(),
  open_count: z.number().int(),
  total_estimate_points: z.number().int(),
  by_status: z.record(z.string(), z.number().int()),
  by_priority: z.record(z.string(), z.number().int()),
  projects: z.array(PortfolioProjectRowSchema),
});
export type PortfolioSummary = z.infer<typeof PortfolioSummarySchema>;

export const DELIVERY_STATUS_ORDER: DeliveryStatus[] = [
  "proposed",
  "planned",
  "in_progress",
  "done",
  "dropped",
];

export const DELIVERY_STATUS_LABELS: Record<DeliveryStatus, string> = {
  proposed: "Proposed",
  planned: "Planned",
  in_progress: "In Progress",
  done: "Done",
  dropped: "Dropped",
};

export const DELIVERY_PRIORITY_ORDER: DeliveryPriority[] = [
  "critical",
  "high",
  "medium",
  "low",
];

export const DELIVERY_PRIORITY_LABELS: Record<DeliveryPriority, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

/** A delivery is publishable to GitHub only while it is proposed/planned and not yet linked. */
export function isPublishable(delivery: Delivery): boolean {
  return (
    (delivery.status === "proposed" || delivery.status === "planned") &&
    !delivery.target_ref
  );
}
