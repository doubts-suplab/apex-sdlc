import { z } from "zod";

// Mirrors GET /api/v1/webhooks/events — recent inbound deliveries (app/api/v1/webhooks.py).
export const WebhookEventSchema = z.object({
  source: z.string(),
  event_type: z.string(),
  delivery_id: z.string(),
  received_at: z.string().nullable(),
});
export type WebhookEvent = z.infer<typeof WebhookEventSchema>;

export const WebhookEventListSchema = z.object({
  total: z.number(),
  items: z.array(WebhookEventSchema),
});
