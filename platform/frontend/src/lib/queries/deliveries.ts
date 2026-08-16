import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { apiFetch } from "@/lib/api";
import {
  Delivery,
  DeliverySchema,
  DeliveryPublishResponse,
  DeliveryPublishResponseSchema,
  PortfolioSummary,
  PortfolioSummarySchema,
} from "@/types/delivery";

/**
 * A project's deliveries (cursor-paginated on the backend; this reads the first page). Backed by
 * GET /api/v1/projects/{id}/deliveries.
 */
export function useProjectDeliveries(projectId: string) {
  return useQuery<Delivery[]>({
    queryKey: ["deliveries", projectId],
    queryFn: async () => {
      const data = await apiFetch<{ items: unknown[] }>(
        `/projects/${projectId}/deliveries/?limit=100`
      );
      return z.array(DeliverySchema).parse(data.items);
    },
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

/**
 * Cross-project delivery rollup for an organisation — counts by status/priority + per-project
 * breakdown. Backed by GET /api/v1/organisations/{id}/portfolio.
 */
export function usePortfolio(organisationId: string | undefined) {
  return useQuery<PortfolioSummary>({
    queryKey: ["portfolio", organisationId],
    queryFn: async () => {
      const data = await apiFetch<unknown>(
        `/organisations/${organisationId}/portfolio`
      );
      return PortfolioSummarySchema.parse(data);
    },
    enabled: !!organisationId,
    staleTime: 30_000,
  });
}

/**
 * Publish a delivery to GitHub as a tracking issue (the write-back seam). On success, refresh both
 * the project's deliveries and any portfolio views. Backed by
 * POST /api/v1/projects/{id}/deliveries/{deliveryId}/publish.
 */
export function usePublishDelivery(projectId: string) {
  const qc = useQueryClient();
  return useMutation<DeliveryPublishResponse, Error, string>({
    mutationFn: async (deliveryId: string) => {
      const data = await apiFetch<unknown>(
        `/projects/${projectId}/deliveries/${deliveryId}/publish`,
        { method: "POST" }
      );
      return DeliveryPublishResponseSchema.parse(data);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["deliveries", projectId] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
    },
  });
}
