import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PhaseType } from "@/types/project";
import {
  AgentRun,
  AgentRunListSchema,
  GateStatus,
  GateStatusListSchema,
  RunPersistResult,
  RunPersistResultSchema,
  StoredArtifact,
  StoredArtifactListSchema,
} from "@/types/agentRun";

/** Stored agent runs for a project. Backed by GET /api/v1/projects/{id}/agent-runs. */
export function useAgentRuns(projectId: string) {
  return useQuery<AgentRun[]>({
    queryKey: ["projects", projectId, "agent-runs"],
    queryFn: async () => {
      const data = await apiFetch<unknown>(`/projects/${projectId}/agent-runs`);
      return AgentRunListSchema.parse(data).items;
    },
    enabled: !!projectId,
    staleTime: 15_000,
  });
}

/** Stored artifacts for a project. Backed by GET /api/v1/projects/{id}/artifacts. */
export function useArtifacts(projectId: string) {
  return useQuery<StoredArtifact[]>({
    queryKey: ["projects", projectId, "artifacts"],
    queryFn: async () => {
      const data = await apiFetch<unknown>(`/projects/${projectId}/artifacts`);
      return StoredArtifactListSchema.parse(data).items;
    },
    enabled: !!projectId,
    staleTime: 15_000,
  });
}

/** Stored phase-gate statuses for a project. Backed by GET /api/v1/projects/{id}/gate-status. */
export function useGateStatus(projectId: string) {
  return useQuery<GateStatus[]>({
    queryKey: ["projects", projectId, "gate-status"],
    queryFn: async () => {
      const data = await apiFetch<unknown>(`/projects/${projectId}/gate-status`);
      return GateStatusListSchema.parse(data).gates;
    },
    enabled: !!projectId,
    staleTime: 15_000,
  });
}

/**
 * Run a single phase agent on the governed harness and persist the run — an approver-persona write.
 * This is the UI surface of the webhook dispatch's execution half (event → project → this run).
 * On success, refresh the project's stored runs, artifacts, gates, and metrics.
 * Backed by POST /api/v1/projects/{id}/phases/{phase}/agents/run-persist.
 */
export function useRunPhase(projectId: string) {
  const qc = useQueryClient();
  return useMutation<RunPersistResult, Error, PhaseType>({
    mutationFn: async (phase: PhaseType) => {
      const data = await apiFetch<unknown>(
        `/projects/${projectId}/phases/${phase}/agents/run-persist`,
        { method: "POST" }
      );
      return RunPersistResultSchema.parse(data);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects", projectId, "agent-runs"] });
      qc.invalidateQueries({ queryKey: ["projects", projectId, "artifacts"] });
      qc.invalidateQueries({ queryKey: ["projects", projectId, "gate-status"] });
      qc.invalidateQueries({ queryKey: ["projects", projectId, "metrics"] });
    },
  });
}
