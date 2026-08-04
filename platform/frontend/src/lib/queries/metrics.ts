import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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

/**
 * Per-persona metering for a persisted project (its stored journey's runs).
 * `model` re-prices the stored token counts illustratively (stub-metered runs cost $0 otherwise).
 * Backed by GET /api/v1/projects/{id}/metrics/cost-latency.
 */
export function useProjectMetrics(projectId: string, model?: string) {
  return useQuery<ReferenceMetrics>({
    queryKey: ["projects", projectId, "metrics", { model }],
    queryFn: async () => {
      const query = model ? `?model=${encodeURIComponent(model)}` : "";
      const data = await apiFetch<unknown>(`/projects/${projectId}/metrics/cost-latency${query}`);
      // The project endpoint omits `project`; supply an empty object to satisfy the shared schema.
      return ReferenceMetricsSchema.parse({ project: {}, ...(data as object) });
    },
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

/**
 * Run + persist a project's governed journey (an approver-persona write). On success, refresh the
 * project's stored metrics. Backed by POST /api/v1/projects/{id}/journey/persist.
 */
export function usePersistJourney(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      apiFetch<{ artifacts: number; agent_runs: number }>(
        `/projects/${projectId}/journey/persist`,
        { method: "POST" }
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects", projectId, "metrics"] });
    },
  });
}
