import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Journey, JourneySchema, ReferenceGates, ReferenceGatesSchema } from "@/types/journey";

/**
 * The reference journey — one project's governed walk through all seven SDLC phases.
 * Optionally filter to a persona's phases. Backed by GET /api/v1/journey/reference.
 */
export function useReferenceJourney(persona?: string) {
  return useQuery<Journey>({
    queryKey: ["journey", "reference", { persona }],
    queryFn: async () => {
      const query = persona ? `?persona=${encodeURIComponent(persona)}` : "";
      const data = await apiFetch<unknown>(`/journey/reference${query}`);
      return JourneySchema.parse(data);
    },
    staleTime: 60_000,
  });
}

/**
 * Phase-gate evaluation across the reference journey, given approved phases.
 * Backed by GET /api/v1/journey/reference/gates?approved=<csv>.
 */
export function useReferenceGates(approved: string[]) {
  const csv = [...approved].sort().join(",");
  return useQuery<ReferenceGates>({
    queryKey: ["journey", "reference", "gates", csv],
    queryFn: async () => {
      const query = csv ? `?approved=${encodeURIComponent(csv)}` : "";
      const data = await apiFetch<unknown>(`/journey/reference/gates${query}`);
      return ReferenceGatesSchema.parse(data);
    },
    staleTime: 60_000,
  });
}
