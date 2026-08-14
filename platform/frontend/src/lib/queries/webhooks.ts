import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { WebhookEvent, WebhookEventListSchema } from "@/types/webhook";

/** Recent inbound webhook deliveries (activity feed). Backed by GET /api/v1/webhooks/events. */
export function useWebhookEvents(limit = 10) {
  return useQuery<WebhookEvent[]>({
    queryKey: ["webhooks", "events", { limit }],
    queryFn: async () => {
      const data = await apiFetch<unknown>(`/webhooks/events?limit=${limit}`);
      return WebhookEventListSchema.parse(data).items;
    },
    staleTime: 15_000,
  });
}
