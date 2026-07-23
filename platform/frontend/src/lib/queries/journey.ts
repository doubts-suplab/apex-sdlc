import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Journey, JourneySchema } from "@/types/journey";

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
