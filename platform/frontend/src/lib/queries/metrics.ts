import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { ReferenceMetrics, ReferenceMetricsSchema } from "@/types/metrics";

/**
 * Per-persona cost / token / latency for the reference journey — the offline cost dashboard.
 * Token counts + latency are real; `cost_usd` is priced at `model` (illustrative, defaults to a
 * reference model server-side). Backed by GET /api/v1/journey/reference/metrics.
 */
export function useReferenceMetrics(model?: string) {
  return useQuery<ReferenceMetrics>({
    queryKey: ["journey", "reference", "metrics", { model }],
    queryFn: async () => {
      const query = model ? `?model=${encodeURIComponent(model)}` : "";
      const data = await apiFetch<unknown>(`/journey/reference/metrics${query}`);
      return ReferenceMetricsSchema.parse(data);
    },
    staleTime: 60_000,
  });
}
