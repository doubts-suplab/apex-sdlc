import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { apiFetch } from "@/lib/api";
import { Integration, IntegrationSchema, IntegrationType } from "@/types/integration";

// ─── Query Keys ──────────────────────────────────────────────────────────────

const integrationKeys = {
  all: (projectId: string) => ["integrations", projectId] as const,
};

// ─── Hooks ───────────────────────────────────────────────────────────────────

export function useProjectIntegrations(projectId: string) {
  return useQuery<Integration[]>({
    queryKey: integrationKeys.all(projectId),
    queryFn: async () => {
      const data = await apiFetch<unknown>(`/projects/${projectId}/integrations`);
      return z.array(IntegrationSchema).parse(data);
    },
    staleTime: 30_000,
    enabled: !!projectId,
  });
}

interface AddIntegrationPayload {
  projectId: string;
  integration_type: IntegrationType;
  config: Record<string, unknown>;
}

export function useAddIntegration() {
  const queryClient = useQueryClient();
  return useMutation<Integration, Error, AddIntegrationPayload>({
    mutationFn: async ({ projectId, integration_type, config }) => {
      const data = await apiFetch<unknown>(
        `/projects/${projectId}/integrations`,
        {
          method: "POST",
          body: JSON.stringify({ integration_type, config }),
        }
      );
      return IntegrationSchema.parse(data);
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: integrationKeys.all(variables.projectId),
      });
    },
  });
}

interface SyncIntegrationPayload {
  projectId: string;
  integrationType: IntegrationType;
}

export function useSyncIntegration() {
  const queryClient = useQueryClient();
  return useMutation<Integration, Error, SyncIntegrationPayload>({
    mutationFn: async ({ projectId, integrationType }) => {
      const data = await apiFetch<unknown>(
        `/projects/${projectId}/integrations/${integrationType}/sync`,
        { method: "POST" }
      );
      return IntegrationSchema.parse(data);
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: integrationKeys.all(variables.projectId),
      });
    },
  });
}
