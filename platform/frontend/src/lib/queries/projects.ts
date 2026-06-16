import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Project, ProjectSchema } from "@/types/project";
import { PaginatedResponse } from "@/types/common";
import { z } from "zod";

export function useProjects(organisationId?: string) {
  return useQuery({
    queryKey: ["projects", { organisationId }],
    queryFn: async () => {
      const params = organisationId ? `?organisation_id=${organisationId}` : "";
      const data = await apiFetch<PaginatedResponse<unknown>>(`/projects${params}`);
      return {
        ...data,
        items: z.array(ProjectSchema).parse(data.items),
      };
    },
    staleTime: 30_000,
  });
}

export function useProject(projectId: string) {
  return useQuery<Project>({
    queryKey: ["projects", projectId],
    queryFn: async () => {
      const data = await apiFetch<unknown>(`/projects/${projectId}`);
      return ProjectSchema.parse(data);
    },
    staleTime: 30_000,
    enabled: !!projectId,
  });
}
