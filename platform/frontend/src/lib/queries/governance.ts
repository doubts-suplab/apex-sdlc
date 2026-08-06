import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
  AuditLogEntry,
  AuditLogListSchema,
  PiiEvent,
  PiiEventListSchema,
  PolicyViolation,
  PolicyViolationListSchema,
} from "@/types/governance";

// All three are CISO/Lead-gated server-side; `enabled` lets the caller withhold the request for a
// non-privileged persona so it never fires a guaranteed-403.

export function useAuditLog(projectId: string, enabled = true) {
  return useQuery<AuditLogEntry[]>({
    queryKey: ["projects", projectId, "governance", "audit-log"],
    queryFn: async () => {
      const data = await apiFetch<unknown>(`/projects/${projectId}/governance/audit-log`);
      return AuditLogListSchema.parse(data).items;
    },
    enabled: !!projectId && enabled,
    staleTime: 15_000,
  });
}

export function usePiiEvents(projectId: string, enabled = true) {
  return useQuery<PiiEvent[]>({
    queryKey: ["projects", projectId, "governance", "pii-events"],
    queryFn: async () => {
      const data = await apiFetch<unknown>(`/projects/${projectId}/governance/pii-events`);
      return PiiEventListSchema.parse(data).items;
    },
    enabled: !!projectId && enabled,
    staleTime: 15_000,
  });
}

export function usePolicyViolations(projectId: string, enabled = true) {
  return useQuery<PolicyViolation[]>({
    queryKey: ["projects", projectId, "governance", "policy-violations"],
    queryFn: async () => {
      const data = await apiFetch<unknown>(`/projects/${projectId}/governance/policy-violations`);
      return PolicyViolationListSchema.parse(data).items;
    },
    enabled: !!projectId && enabled,
    staleTime: 15_000,
  });
}
